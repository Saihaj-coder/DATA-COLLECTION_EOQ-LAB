"""Helpers for national CRDC + ed-tech data collection (used by notebooks)."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import pandas as pd
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; EOQ-Lab-Federal-Collection/1.0; "
        "academic research; public data)"
    )
}

CATEGORIES = [
    "test_scores",
    "enrollment",
    "financials",
    "teachers",
    "discipline",
    "other",
]

ED_GOV_CKAN_API = "https://data.ed.gov/api/3/action"

# Public-use CRDC zip bundles (national, all states)
CRDC_PUBLIC_ZIPS = [
    {
        "year": "2015-16",
        "url": "https://civilrightsdata.ed.gov/assets/ocr/docs/2015-16-crdc-data.zip",
        "filename": "2015-16-crdc-data.zip",
    },
    {
        "year": "2017-18",
        "url": "https://civilrightsdata.ed.gov/assets/ocr/docs/2017-18-crdc-data.zip",
        "filename": "2017-18-crdc-data.zip",
    },
    {
        "year": "2020-21",
        "url": "https://civilrightsdata.ed.gov/assets/ocr/docs/2020-21-crdc-data.zip",
        "filename": "2020-21-crdc-data.zip",
    },
    {
        "year": "2021-22",
        "url": "https://civilrightsdata.ed.gov/assets/ocr/docs/2021-22-crdc-data.zip",
        "filename": "2021-22-crdc-data.zip",
        "note": "Very large (~800 MB). Optional.",
    },
]

CRDC_API_YEAR_TAGS = ("2015-16", "2015-2016", "2020-21", "2020-2021", "2021-22", "2021-2022")
CRDC_ALLOWED_FORMATS = {"CSV", "XLSX", "XLS", "ZIP"}

TECH_TOPIC_KEYWORDS = (
    "internet",
    "wifi",
    "wi-fi",
    "computer",
    "device",
    "technology",
    "digital",
    "distance",
    "broadband",
    "edtech",
    "ed-tech",
)

EDTECH_ALLOWED_FORMATS = {"CSV", "XLSX", "XLS", "ZIP", "ZIPPED DAT", "ZIPPED SAS", "ZIPPED CSV"}

# Core NCES FRSS technology surveys (direct download — always include)
EDTECH_KNOWN_DOWNLOADS = [
    {
        "dataset_title": "Educational Technology in Public Schools, 2008",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f92data.zip",
        "description": "Ed-tech: Educational Technology in Public Schools, 2008 — survey data",
    },
    {
        "dataset_title": "Educational Technology in Public School Districts, 2008",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f93data.zip",
        "description": "Ed-tech: Educational Technology in Public School Districts, 2008 — survey data",
    },
    {
        "dataset_title": "Internet Access in U.S. Public Schools, 2003",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f86data.zip",
        "description": "Ed-tech: Internet Access in U.S. Public Schools, 2003 — survey data",
    },
    {
        "dataset_title": "Teachers' Use of Educational Technology in U.S. Public Schools, 2009",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f95data.zip",
        "description": "Ed-tech: Teachers' Use of Educational Technology, 2009 — survey data",
    },
]

EDTECH_SEARCH_QUERIES = (
    "Educational Technology in Public Schools",
    "Educational Technology in Public School Districts",
    "Internet Access in U.S. Public Schools",
    "Teachers' Use of Educational Technology",
    "digital learning schools",
)


def resolve_project_root(cwd: Path | None = None) -> Path:
    cwd = cwd or Path.cwd()
    if cwd.name == "notebooks":
        return cwd.parent
    if (cwd / "notebooks").is_dir() and (cwd / "data").is_dir():
        return cwd
    if (cwd.parent / "data").exists():
        return cwd.parent
    return cwd


def ensure_federal_layout(project_root: Path) -> dict[str, Path]:
    data_raw = project_root / "data" / "raw"
    paths = {
        "project_root": project_root,
        "data_raw": data_raw,
        "federal_root": data_raw / "federal",
        "crdc_root": data_raw / "federal" / "crdc",
        "edtech_root": data_raw / "federal" / "edtech",
        "logs_dir": project_root / "logs",
    }
    for folder in [paths["federal_root"], paths["crdc_root"], paths["edtech_root"], paths["logs_dir"]]:
        folder.mkdir(parents=True, exist_ok=True)
    for year in ["2015-16", "2017-18", "2020-21", "2021-22"]:
        (paths["crdc_root"] / year).mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES:
        (paths["federal_root"] / category).mkdir(parents=True, exist_ok=True)
    return paths


def _filename_from_url(url: str, response: requests.Response) -> str:
    cd = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="?([^";]+)"?', cd)
    if match:
        return match.group(1).strip()
    path_name = Path(unquote(urlparse(url).path)).name
    return path_name or "download.bin"


def guess_category(text: str) -> str:
    t = text.lower()
    rules = [
        ("discipline", ("discipline", "suspension", "expulsion", "arrest", "bullying", "restraint", "seclusion", "offense", "corporal")),
        ("test_scores", ("ap ", "advanced placement", "sat", "act", "algebra", "geometry", "calculus", "biology", "chemistry", "physics", "pass rate", "assessment", "proficiency")),
        ("enrollment", ("enrollment", "membership", "student count", "demographic", "race", "lep", "disability", "gifted", "prekindergarten")),
        ("teachers", ("teacher", "staff", "personnel", "certification", "classroom teacher")),
        ("financials", ("expenditure", "finance", "fiscal", "budget", "revenue", "per pupil")),
        ("other", ("internet", "wifi", "computer", "device", "technology", "digital", "distance education", "broadband")),
    ]
    for category, keywords in rules:
        if any(k in t for k in keywords):
            return category
    return "other"


def filename_from_url_path(url: str) -> str:
    """Safe local filename from URL path (ignores ?query so ArcGIS links don't become 'csv')."""
    path_name = Path(unquote(urlparse(url).path)).name
    return path_name or "download.bin"


def is_direct_crdc_api_url(url: str) -> bool:
    """Keep real file downloads; drop ArcGIS map/API links that often 404 in scripts."""
    blocked = (
        "opendata.arcgis.com",
        "arcgis.com/sharing",
        "arcgis/rest/services",
        "/maps/nces::",
    )
    u = url.lower()
    if any(b in u for b in blocked):
        return False
    return filename_from_url_path(url).lower().endswith((".xlsx", ".xls", ".csv", ".zip"))


def filter_crdc_api_downloads(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[df["url"].map(is_direct_crdc_api_url)].copy()
    return out.drop_duplicates(subset=["url"]).reset_index(drop=True)


def crdc_api_dest_filename(row: pd.Series) -> str:
    """Unique filename per year so 2015-16 files do not collide with 2017-18 names."""
    fname = filename_from_url_path(row["url"])
    hint = str(row.get("year_hint", "") or "")
    for tag in ("2015-16", "2015-2016", "2020-21", "2020-2021", "2021-22", "2021-2022"):
        if tag in hint or tag in row.get("dataset_title", "") or tag in row.get("url", ""):
            year = tag.replace("2015-2016", "2015-16").replace("2020-2021", "2020-21").replace(
                "2021-2022", "2021-22"
            )
            if not fname.startswith(year):
                return f"{year}_{fname}"
    return fname


def safe_filename(name: str) -> str:
    """Make a string safe for Windows file names."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name)
    return cleaned[:200] or "download.bin"


def is_direct_edtech_url(url: str) -> bool:
    """Keep real survey/data files; drop ArcGIS map API links."""
    blocked = (
        "opendata.arcgis.com",
        "arcgis.com/sharing",
        "arcgis/rest/services",
        "/maps/nces::",
    )
    u = url.lower()
    if any(b in u for b in blocked):
        return False
    fname = filename_from_url_path(url).lower()
    return fname.endswith((".xlsx", ".xls", ".csv", ".zip"))


def filter_edtech_downloads(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[df["url"].map(is_direct_edtech_url)].copy()
    return out.drop_duplicates(subset=["url"]).reset_index(drop=True)


def edtech_dest_filename(row: pd.Series) -> str:
    return safe_filename(filename_from_url_path(row["url"]))


def download_to_path(
    url: str,
    dest_path: Path,
    description: str,
    *,
    state: str = "federal",
    category: str = "other",
    download_log: Path,
    project_root: Path | None = None,
    skip_if_exists: bool = True,
    timeout_seconds: int = 600,
) -> dict:
    dest_path = dest_path.parent / safe_filename(dest_path.name)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout_seconds,
            stream=True,
        ) as response:
            response.raise_for_status()
            if dest_path.name in ("download.bin", "") or not dest_path.suffix:
                dest_path = dest_path.parent / safe_filename(_filename_from_url(url, response))

            if skip_if_exists and dest_path.exists() and dest_path.stat().st_size > 0:
                local_path = str(dest_path.relative_to(project_root)) if project_root else str(dest_path)
                record = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "skipped_exists",
                    "state": state,
                    "category": category,
                    "description": description,
                    "url": url,
                    "local_path": local_path,
                    "bytes": dest_path.stat().st_size,
                }
                _append_log(download_log, record)
                return record

            bytes_written = 0
            with dest_path.open("wb") as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        out_file.write(chunk)
                        bytes_written += len(chunk)
    except (requests.RequestException, OSError) as err:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "state": state,
            "category": category,
            "description": description,
            "url": url,
            "local_path": "",
            "bytes": 0,
            "error": str(err),
        }
        _append_log(download_log, record)
        return record

    local_path = str(dest_path.relative_to(project_root)) if project_root else str(dest_path)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "downloaded",
        "state": state,
        "category": category,
        "description": description,
        "url": url,
        "local_path": local_path,
        "bytes": bytes_written,
    }
    _append_log(download_log, record)
    return record


def _append_log(download_log: Path, record: dict) -> None:
    download_log.parent.mkdir(parents=True, exist_ok=True)
    with download_log.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")


def refresh_manifest(download_log: Path, manifest_csv: Path) -> pd.DataFrame:
    if not download_log.exists():
        return pd.DataFrame()
    rows = []
    with download_log.open(encoding="utf-8") as log_file:
        for line in log_file:
            if line.strip():
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(manifest_csv, index=False)
    return df


def edgov_package_search(query: str, rows: int = 100, start: int = 0, retries: int = 3) -> dict:
    url = f"{ED_GOV_CKAN_API}/package_search"
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                params={"q": query, "rows": rows, "start": start},
                headers=DEFAULT_HEADERS,
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise RuntimeError(payload)
            return payload["result"]
        except (requests.RequestException, RuntimeError) as err:
            last_error = err
            if attempt + 1 == retries:
                raise
    raise last_error  # pragma: no cover


def discover_crdc_api_files() -> pd.DataFrame:
    """Find CRDC spreadsheet downloads for recent cycles (targeted searches)."""
    rows = []
    seen = set()
    queries = (
        "2015-16 civil rights data collection",
        "2020-21 civil rights data collection",
        "2021-22 civil rights data collection",
    )

    for query in queries:
        start = 0
        while True:
            page = edgov_package_search(query, rows=100, start=start)
            batch = page["results"]
            for package in batch:
                title = package.get("title") or ""
                for resource in package.get("resources", []):
                    fmt = (resource.get("format") or "").upper().strip()
                    url = (resource.get("url") or "").strip()
                    if not url or fmt not in CRDC_ALLOWED_FORMATS or url in seen:
                        continue
                    if not any(tag in url or tag in title for tag in CRDC_API_YEAR_TAGS):
                        continue
                    seen.add(url)
                    rows.append(
                        {
                            "source": "CRDC",
                            "year_hint": next(
                                (t for t in CRDC_API_YEAR_TAGS if t in title or t in url), ""
                            ),
                            "category": guess_category(title + " " + url),
                            "dataset_title": title,
                            "format": fmt,
                            "url": url,
                            "description": f"CRDC: {title} — {resource.get('name') or fmt}",
                        }
                    )
            start += 100
            if start >= page["count"] or not batch:
                break

    return filter_crdc_api_downloads(pd.DataFrame(rows))


def discover_edtech_files() -> pd.DataFrame:
    rows = []
    seen = set()

    for item in EDTECH_KNOWN_DOWNLOADS:
        url = item["url"]
        seen.add(url)
        rows.append(
            {
                "source": "NCES/FRSS",
                "category": "other",
                "dataset_title": item["dataset_title"],
                "format": item["format"],
                "url": url,
                "description": item["description"],
            }
        )

    for query in EDTECH_SEARCH_QUERIES:
        try:
            page = edgov_package_search(query, rows=20, start=0)
        except requests.RequestException as err:
            print(f"  SKIP search (API error): {query!r} -> {err}")
            continue
        for package in page["results"]:
            title = package.get("title") or ""
            for resource in package.get("resources", []):
                fmt = (resource.get("format") or "").upper().strip()
                url = (resource.get("url") or "").strip()
                if not url or fmt not in EDTECH_ALLOWED_FORMATS:
                    continue
                if url in seen:
                    continue
                seen.add(url)
                rows.append(
                    {
                        "source": "NCES/ED",
                        "category": "other",
                        "dataset_title": title,
                        "format": fmt,
                        "url": url,
                        "description": f"Ed-tech: {title} — {resource.get('name') or fmt}",
                    }
                )
    return filter_edtech_downloads(pd.DataFrame(rows))


def list_crdc_zip_topics(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return sorted({Path(n).stem for n in zf.namelist() if n.lower().endswith(".csv")})


def inventory_crdc_zips(crdc_root: Path) -> pd.DataFrame:
    rows = []
    for zip_path in sorted(crdc_root.rglob("*.zip")):
        year = zip_path.parent.name
        try:
            topics = list_crdc_zip_topics(zip_path)
        except zipfile.BadZipFile as err:
            rows.append(
                {
                    "year": year,
                    "zip_file": zip_path.name,
                    "topics": 0,
                    "tech_topics": 0,
                    "error": str(err),
                }
            )
            continue
        tech_topics = [t for t in topics if any(k in t.lower() for k in TECH_TOPIC_KEYWORDS)]
        rows.append(
            {
                "year": year,
                "zip_file": zip_path.name,
                "topics": len(topics),
                "tech_topics": len(tech_topics),
                "tech_topic_names": "; ".join(tech_topics[:8]),
                "error": "",
            }
        )
    return pd.DataFrame(rows)


def count_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())
