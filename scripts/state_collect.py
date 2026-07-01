"""Shared helpers for state-level education data collection (Colorado, Texas, …)."""

from __future__ import annotations

import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from federal_collect import DEFAULT_HEADERS, _append_log, download_to_path, safe_filename

STATE_SLUGS = ("colorado", "texas")
STATE_ABBRS = {"colorado": "CO", "texas": "TX"}

CATEGORIES = [
    "test_scores",
    "enrollment",
    "financials",
    "teachers",
    "discipline",
    "other",
]

HTML_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FILE_EXTENSIONS = (".csv", ".xlsx", ".xls", ".zip", ".pdf", ".txt")


def resolve_project_root(cwd: Path | None = None) -> Path:
    cwd = cwd or Path.cwd()
    if cwd.name == "notebooks":
        return cwd.parent
    if (cwd / "notebooks").is_dir() and (cwd / "data").is_dir():
        return cwd
    if (cwd.parent / "data").exists():
        return cwd.parent
    return cwd


def ensure_state_layout(project_root: Path, states: tuple[str, ...] = STATE_SLUGS) -> dict[str, Path]:
    data_raw = project_root / "data" / "raw"
    data_cleaned = project_root / "data" / "cleaned"
    logs_dir = project_root / "logs"
    paths = {
        "project_root": project_root,
        "data_raw": data_raw,
        "data_cleaned": data_cleaned,
        "logs_dir": logs_dir,
    }
    for folder in (data_raw, data_cleaned, logs_dir):
        folder.mkdir(parents=True, exist_ok=True)
    for state in states:
        for category in CATEGORIES:
            (data_raw / state / category).mkdir(parents=True, exist_ok=True)
            (data_cleaned / state / category).mkdir(parents=True, exist_ok=True)
    return paths


def guess_category(title: str, description: str = "") -> str:
    """Keyword-based folder assignment (extend with state-specific terms)."""
    text = f"{title} {description}".lower()
    rules = [
        (
            "test_scores",
            [
                "staar", "cmas", "psat", "sat", "act", "assessment", "test score",
                "pass rate", "proficiency", "accountability rating", "tapr", "aeis",
                "telpas", "algebra", "biology", "chemistry", "physics", "ap ",
            ],
        ),
        (
            "enrollment",
            [
                "enrollment", "membership", "student count", "demographic", "mobility",
                "stability", "attendance", "english learner", "lep", "graduation rate",
                "dropout", "retention",
            ],
        ),
        (
            "financials",
            [
                "finance", "financial", "expenditure", "budget", "revenue", "per pupil",
                "peims", "fiscal", "salary", "compensation", "facilities",
            ],
        ),
        (
            "teachers",
            [
                "teacher", "staff", "personnel", "educator", "certification", "superintendent",
                "principal", "tlcc", "working conditions",
            ],
        ),
        (
            "discipline",
            [
                "discipline", "suspension", "expulsion", "bullying", "harassment",
                "offense", "restraint", "seclusion", "crime", "safety",
            ],
        ),
    ]
    for category, keywords in rules:
        if any(word in text for word in keywords):
            return category
    return "other"


def download_state_rows(
    catalog: pd.DataFrame,
    project_root: Path,
    download_log: Path,
    *,
    seconds_between: float = 0.5,
) -> list[dict]:
    """Download rows from a discovery catalog (must have state, category, url, description)."""
    records: list[dict] = []
    for _, row in catalog.iterrows():
        state = str(row["state"]).lower()
        category = str(row.get("category", "other"))
        dest_name = row.get("dest_filename") or safe_filename(
            Path(urlparse(row["url"]).path).name or f"{row.get('dataset_id', 'dataset')}.csv"
        )
        dest_path = project_root / "data" / "raw" / state / category / dest_name
        record = download_to_path(
            row["url"],
            dest_path,
            str(row.get("description", row.get("dataset_title", ""))),
            state=state,
            category=category,
            download_log=download_log,
            project_root=project_root,
            timeout_seconds=600,
        )
        records.append(record)
        if seconds_between > 0:
            time.sleep(seconds_between)
    return records


def _request_with_retry(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    max_retries: int = 8,
    timeout: int = 90,
    allow_redirects: bool = True,
) -> requests.Response:
    """HTTP request with exponential backoff on 429 Too Many Requests."""
    last: requests.Response | None = None
    for attempt in range(max_retries):
        last = requests.request(
            method,
            url,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        if last.status_code != 429:
            return last
        retry_after = last.headers.get("Retry-After")
        wait = float(retry_after) if retry_after else min(2**attempt, 60)
        time.sleep(wait)
    assert last is not None
    return last


def socrata_is_exportable(
    portal_base: str,
    dataset_id: str,
    cache: dict[str, bool] | None = None,
    *,
    seconds_between: float = 0.0,
) -> bool:
    """
    Return True only for Socrata datasets with a working CSV export.

    Map-only and story views return 404 on rows.csv; tabular views export.
    """
    cache = cache if cache is not None else {}
    if dataset_id in cache:
        return cache[dataset_id]

    base = portal_base.rstrip("/")
    meta_url = f"{base}/api/views/{dataset_id}.json"
    response = _request_with_retry("GET", meta_url, timeout=30)
    if not response.ok:
        cache[dataset_id] = False
        if seconds_between > 0:
            time.sleep(seconds_between)
        return False

    view_type = (response.json().get("viewType") or "").lower()
    if view_type == "tabular":
        cache[dataset_id] = True
        if seconds_between > 0:
            time.sleep(seconds_between)
        return True

    csv_url = f"{base}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
    head = _request_with_retry("HEAD", csv_url, timeout=30, allow_redirects=True)
    exportable = head.status_code == 200
    cache[dataset_id] = exportable
    if seconds_between > 0:
        time.sleep(seconds_between)
    return exportable


def socrata_catalog_page(
    portal_base: str,
    query: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """One page of Socrata catalog search (Colorado + Texas open data portals)."""
    url = f"{portal_base.rstrip('/')}/api/catalog/v1"
    params = {"q": query, "only": "datasets", "limit": limit, "offset": offset}
    response = _request_with_retry("GET", url, params=params, timeout=90)
    response.raise_for_status()
    return response.json()


def discover_socrata_datasets(
    portal_base: str,
    search_queries: list[str],
    state_slug: str,
    *,
    attribution_keywords: tuple[str, ...] = (),
    max_per_query: int = 300,
    exportable_only: bool = True,
    seconds_between_checks: float = 0.25,
) -> pd.DataFrame:
    """
    Discover datasets on a Socrata portal (data.colorado.gov or data.texas.gov).

    Returns a catalog with direct CSV export URLs.
    """
    rows: list[dict] = []
    seen_ids: set[str] = set()
    export_cache: dict[str, bool] = {}

    for query in search_queries:
        offset = 0
        page_size = 100
        fetched = 0
        while fetched < max_per_query:
            try:
                payload = socrata_catalog_page(portal_base, query, limit=page_size, offset=offset)
            except requests.HTTPError as err:
                if err.response is not None and err.response.status_code == 429:
                    print(
                        f"  Socrata rate limit on {state_slug!r} query={query!r} "
                        f"(offset={offset}); keeping {len(rows)} datasets discovered so far"
                    )
                    break
                raise
            results = payload.get("results") or []
            if not results:
                break
            for item in results:
                resource = item.get("resource") or {}
                dataset_id = resource.get("id")
                if not dataset_id or dataset_id in seen_ids:
                    continue
                name = resource.get("name") or dataset_id
                description = resource.get("description") or ""
                attribution = (resource.get("attribution") or "").lower()
                if attribution_keywords and not any(k.lower() in attribution for k in attribution_keywords):
                    # Also allow name/description match when attribution is empty
                    blob = f"{name} {description} {attribution}".lower()
                    if not any(k.lower() in blob for k in attribution_keywords):
                        continue
                seen_ids.add(dataset_id)
                if exportable_only and not socrata_is_exportable(
                    portal_base,
                    dataset_id,
                    export_cache,
                    seconds_between=seconds_between_checks,
                ):
                    continue
                csv_url = f"{portal_base.rstrip('/')}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
                rows.append(
                    {
                        "state": state_slug,
                        "source": "Socrata",
                        "dataset_id": dataset_id,
                        "dataset_title": name,
                        "description": f"{state_slug.title()} open data: {name}",
                        "category": guess_category(name, description),
                        "url": csv_url,
                        "dest_filename": safe_filename(f"socrata_{dataset_id}.csv"),
                        "format": "CSV",
                    }
                )
            fetched += len(results)
            offset += page_size
            if len(results) < page_size:
                break
            if seconds_between_checks > 0:
                time.sleep(seconds_between_checks)

    return pd.DataFrame(rows)


def harvest_html_file_links(page_url: str, *, same_domain_only: bool = True) -> list[dict]:
    """BeautifulSoup: collect direct file links from a state DOE index page."""
    response = requests.get(page_url, headers=HTML_HEADERS, timeout=90)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    base_domain = urlparse(page_url).netloc
    links: list[dict] = []
    seen: set[str] = set()

    def add_link(full_url: str, link_text: str) -> None:
        if full_url in seen:
            return
        seen.add(full_url)
        links.append({"url": full_url, "link_text": link_text})

    # Standard anchors ending in a file extension
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        full_url = urljoin(page_url, href)
        parsed = urlparse(full_url)
        if same_domain_only and parsed.netloc and parsed.netloc != base_domain:
            continue
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in FILE_EXTENSIONS):
            link_text = tag.get_text(" ", strip=True) or Path(parsed.path).name
            add_link(full_url, link_text)

    # Colorado CDE: links use data-file-name + /fs/resource-manager/view/{uuid}
    for tag in soup.find_all("a", href=True):
        data_file = tag.get("data-file-name")
        if not data_file:
            continue
        full_url = urljoin(page_url, tag["href"])
        add_link(full_url, data_file)

    # Regex fallback (attribute order may vary in HTML)
    for match in re.finditer(
        r'data-file-name="([^"]+)"[^>]*href="([^"]+)"', response.text, re.I
    ):
        add_link(urljoin(page_url, match.group(2)), match.group(1))

    return links


def discover_html_seed_pages(
    seed_urls: list[str],
    state_slug: str,
    *,
    page_label: str = "",
) -> pd.DataFrame:
    """Run harvest_html_file_links on each seed URL and build a download catalog."""
    rows: list[dict] = []
    for seed in seed_urls:
        try:
            links = harvest_html_file_links(seed)
        except requests.RequestException as err:
            rows.append(
                {
                    "state": state_slug,
                    "source": "HTML",
                    "dataset_title": f"SCRAPE FAILED: {seed}",
                    "description": str(err),
                    "category": "other",
                    "url": "",
                    "dest_filename": "",
                    "format": "ERROR",
                }
            )
            continue
        for link in links:
            title = link["link_text"]
            rows.append(
                {
                    "state": state_slug,
                    "source": "HTML",
                    "dataset_title": title,
                    "description": f"{state_slug.title()} {page_label}: {title} from {seed}",
                    "category": guess_category(title, seed),
                    "url": link["url"],
                    "dest_filename": safe_filename(Path(urlparse(link["url"]).path).name),
                    "format": Path(urlparse(link["url"]).path).suffix.lstrip(".").upper(),
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df["url"].astype(str).str.len() > 0].drop_duplicates(subset=["url"]).reset_index(drop=True)


def direct_download_catalog(state_slug: str, items: list[dict]) -> pd.DataFrame:
    """Build a catalog from hand-picked direct URLs."""
    rows = []
    for item in items:
        rows.append(
            {
                "state": state_slug,
                "source": "Direct",
                "dataset_title": item["dataset_title"],
                "description": item.get("description", item["dataset_title"]),
                "category": item.get("category") or guess_category(item["dataset_title"]),
                "url": item["url"],
                "dest_filename": item.get("dest_filename")
                or safe_filename(Path(urlparse(item["url"]).path).name),
                "format": item.get("format", "FILE"),
            }
        )
    return pd.DataFrame(rows)


def _log_cleaned_file(
    download_log: Path,
    project_root: Path,
    state_slug: str,
    category: str,
    description: str,
    out_path: Path,
    source_url: str,
    rows: int,
) -> None:
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "cleaned_extract",
        "state": state_slug,
        "category": category,
        "description": description,
        "url": source_url,
        "local_path": str(out_path.relative_to(project_root)),
        "bytes": out_path.stat().st_size if out_path.exists() else 0,
        "rows": rows,
    }
    _append_log(download_log, record)


def filter_nces_ccd_for_state(
    project_root: Path,
    state_slug: str,
    state_abbr: str,
    download_log: Path,
) -> dict | None:
    """Filter NCES CCD school universe zip to one state → data/cleaned/{state}/."""
    enrollment_dir = project_root / "data" / "raw" / "federal" / "enrollment"
    zips = sorted(enrollment_dir.glob("ccd_sch_*csv.zip"))
    if not zips:
        return None
    zip_path = zips[-1]
    cleaned_root = project_root / "data" / "cleaned" / state_slug / "enrollment"
    cleaned_root.mkdir(parents=True, exist_ok=True)
    out_path = cleaned_root / f"nces_public_schools_{state_abbr}.csv"

    if out_path.exists() and out_path.stat().st_size > 0:
        return {"status": "skipped_exists", "local_path": str(out_path), "rows": 0}

    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(csv_name) as handle:
            try:
                df = pd.read_csv(handle, low_memory=False, encoding="utf-8")
            except UnicodeDecodeError:
                handle.seek(0)
                df = pd.read_csv(handle, low_memory=False, encoding="latin-1")

    if "ST" not in df.columns:
        return None
    state_df = df[df["ST"] == state_abbr].copy()
    if state_df.empty:
        return None
    state_df.to_csv(out_path, index=False)
    _log_cleaned_file(
        download_log,
        project_root,
        state_slug,
        "enrollment",
        f"NCES CCD public schools filtered to {state_abbr}",
        out_path,
        str(zip_path),
        len(state_df),
    )
    return {"status": "written", "local_path": str(out_path), "rows": len(state_df)}


def filter_nces_f33_for_state(
    project_root: Path,
    state_slug: str,
    state_abbr: str,
    download_log: Path,
) -> dict | None:
    """Filter NCES CCD district finance (F-33) zip to one state → data/cleaned/{state}/financials/."""
    finance_dir = project_root / "data" / "raw" / "federal" / "financials"
    zips = sorted(finance_dir.glob("Sdf*_1a.zip")) + sorted(finance_dir.glob("sdf*_1a.zip"))
    if not zips:
        return None

    zip_path = zips[-1]
    cleaned_root = project_root / "data" / "cleaned" / state_slug / "financials"
    cleaned_root.mkdir(parents=True, exist_ok=True)
    out_path = cleaned_root / f"nces_district_finance_{state_abbr}.csv"

    if out_path.exists() and out_path.stat().st_size > 0:
        return {"status": "skipped_exists", "local_path": str(out_path), "rows": 0}

    with zipfile.ZipFile(zip_path) as zf:
        data_name = next(
            (n for n in zf.namelist() if n.lower().endswith((".txt", ".csv"))),
            None,
        )
        if not data_name:
            return None
        sep = "\t" if data_name.lower().endswith(".txt") else ","
        with zf.open(data_name) as handle:
            try:
                df = pd.read_csv(handle, sep=sep, low_memory=False, encoding="utf-8")
            except UnicodeDecodeError:
                handle.seek(0)
                df = pd.read_csv(handle, sep=sep, low_memory=False, encoding="latin-1")

    state_col = next(
        (c for c in ("STABBR", "ST", "STATE_ABBR", "LEA_STATE") if c in df.columns),
        None,
    )
    if not state_col:
        return None

    state_df = df[df[state_col].astype(str).str.upper() == state_abbr.upper()].copy()
    if state_df.empty:
        return None

    state_df.to_csv(out_path, index=False)
    _log_cleaned_file(
        download_log,
        project_root,
        state_slug,
        "financials",
        f"NCES CCD district finance (F-33) filtered to {state_abbr}",
        out_path,
        str(zip_path),
        len(state_df),
    )
    return {"status": "written", "local_path": str(out_path), "rows": len(state_df)}


def filter_crdc_extracted_for_state(
    project_root: Path,
    state_slug: str,
    state_abbr: str,
    download_log: Path,
) -> list[dict]:
    """
    Filter files already in data/raw/federal/crdc_extracted/ to state rows.

    Writes to data/cleaned/{state}/{category}/crdc_{topic}_{ABBR}.csv
    """
    extract_root = project_root / "data" / "raw" / "federal" / "crdc_extracted"
    cleaned_base = project_root / "data" / "cleaned" / state_slug
    written: list[dict] = []

    if not extract_root.exists():
        return written

    for csv_path in sorted(extract_root.rglob("*.csv")):
        topic_name = csv_path.stem
        try:
            df = pd.read_csv(csv_path, low_memory=False, encoding="latin-1")
        except Exception:
            try:
                df = pd.read_csv(csv_path, low_memory=False)
            except Exception as err:
                print(f"  SKIP read error: {csv_path.name} -> {err}")
                continue

        if "LEA_STATE" not in df.columns:
            continue
        state_df = df[df["LEA_STATE"] == state_abbr].copy()
        if state_df.empty:
            continue

        category = guess_category(topic_name)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", topic_name)[:80]
        out_path = cleaned_base / category / f"crdc_{safe_name}_{state_abbr}.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and out_path.stat().st_size > 0:
            written.append({"status": "skipped_exists", "topic": topic_name, "rows": len(state_df)})
            continue

        state_df.to_csv(out_path, index=False)
        _log_cleaned_file(
            download_log,
            project_root,
            state_slug,
            category,
            f"CRDC extract filtered to {state_abbr}: {topic_name}",
            out_path,
            str(csv_path),
            len(state_df),
        )
        written.append(
            {
                "status": "written",
                "topic": topic_name,
                "category": category,
                "rows": len(state_df),
                "local_path": str(out_path.relative_to(project_root)),
            }
        )
    return written


def state_collection_summary(project_root: Path, state_slug: str) -> pd.DataFrame:
    """File counts for raw + cleaned layers."""
    raw_root = project_root / "data" / "raw" / state_slug
    clean_root = project_root / "data" / "cleaned" / state_slug
    rows = []
    for label, root in (("raw", raw_root), ("cleaned", clean_root)):
        if not root.exists():
            continue
        for cat in CATEGORIES:
            cat_dir = root / cat
            count = sum(1 for p in cat_dir.rglob("*") if p.is_file()) if cat_dir.exists() else 0
            if count:
                rows.append({"layer": label, "category": cat, "files": count})
        total = sum(1 for p in root.rglob("*") if p.is_file())
        rows.append({"layer": label, "category": "TOTAL", "files": total})
    return pd.DataFrame(rows)
