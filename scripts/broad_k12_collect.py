"""Helpers for broader national K-12 data (enrollment, finance, staffing, facilities)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from federal_collect import (
    DEFAULT_HEADERS,
    SPP_APP_JS_URL,
    SPP_BASE_URL,
    _spp_stem_category,
    download_to_path,
    edtech_dest_filename,
    filter_edtech_downloads,
    safe_filename,
)

NCES_SCHOOL_CATALOG = "https://nces.ed.gov/ccd/pubschuniv.asp"
NCES_STATE_CATALOG = "https://nces.ed.gov/ccd/stnfis.asp"
NCES_DISTRICT_FINANCE_CATALOG = "https://nces.ed.gov/ccd/f33agency.asp"

HTML_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# School Pulse Panel — enrollment, staffing, facilities, college readiness (not civil-rights/ed-tech)
SPP_BROAD_K12_STEMS = (
    "Staffing",
    "StaffVac",
    "SchoolFac",
    "PhysEd",
    "CCReadiness",
    "Assessment",
    "civics",
    "Arts",
    "AfterSchoolPrograms",
    "FamilyEngagement",
    "FoodServices",
    "SummerPrograms",
    "Tutoring",
    "Transportation",
    "Housing",
)

FRSS_BROAD_K12_DOWNLOADS = [
    {
        "dataset_title": "Condition of Public School Facilities, 2012-13 (FRSS 105)",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f105data.zip",
        "description": "K-12: FRSS 105 school facilities condition — survey data",
        "category": "financials",
    },
    {
        "dataset_title": "Condition of Public School Facilities, 2012-13 (FRSS 105) — documentation",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f105doc.zip",
        "description": "K-12: FRSS 105 school facilities — documentation",
        "category": "financials",
    },
    {
        "dataset_title": "Dual Credit and Exam-Based Courses, 2010-11 (FRSS 104)",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f104data.zip",
        "description": "K-12: FRSS 104 dual credit / exam-based courses — survey data",
        "category": "test_scores",
    },
    {
        "dataset_title": "Programs and Services for High School English Learners (FRSS 107)",
        "format": "ZIP",
        "url": "https://nces.ed.gov/surveys/frss/download/data/f107data.zip",
        "description": "K-12: FRSS 107 high school English learner programs — survey data",
        "category": "enrollment",
    },
]


def harvest_nces_zip_links(catalog_url: str) -> list[str]:
    """Return all .zip links on an NCES CCD catalog page."""
    response = requests.get(catalog_url, headers=HTML_HEADERS, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        full_url = urljoin(catalog_url, tag["href"])
        if full_url.lower().endswith(".zip"):
            links.append(full_url)
    return list(dict.fromkeys(links))


def pick_newest_ccd_school_csv_zip(links: list[str]) -> str | None:
    candidates = [u for u in links if "ccd_sch_029" in u.lower() and "csv" in u.lower()]
    if not candidates:
        return None

    def year_key(url: str) -> int:
        match = re.search(r"_(\d{4})_", url)
        return int(match.group(1)) if match else 0

    return max(candidates, key=year_key)


def pick_newest_state_nonfiscal_zip(links: list[str]) -> str | None:
    candidates = [
        u
        for u in links
        if u.lower().endswith(".zip") and "xls" in u.lower() and "documentation" not in u.lower()
    ]
    if not candidates:
        return None

    def key(url: str) -> int:
        match = re.search(r"st(\d{2,3})", url.lower())
        return int(match.group(1)) if match else 0

    return max(candidates, key=key)


def pick_newest_f33_zip(links: list[str]) -> str | None:
    """Newest Census F-33 / school district finance data zip from NCES catalog."""
    skip = ("spss_code", "sas7bdat", "documentation", "_flat", "_sas", "/f33/")
    candidates = [
        u
        for u in links
        if re.search(r"sdf\d{2}_1a\.zip", u, re.I)
        and not any(token in u.lower() for token in skip)
    ]
    if not candidates:
        return None

    def key(url: str) -> int:
        match = re.search(r"sdf(\d{2})", url.lower())
        return int(match.group(1)) if match else 0

    return max(candidates, key=key)


def discover_nces_ccd_downloads() -> pd.DataFrame:
    """School universe CSV zip, state nonfiscal zip, and district finance (F-33) if available."""
    rows = []
    school_links = harvest_nces_zip_links(NCES_SCHOOL_CATALOG)
    state_links = harvest_nces_zip_links(NCES_STATE_CATALOG)
    finance_links = harvest_nces_zip_links(NCES_DISTRICT_FINANCE_CATALOG)

    best_school = pick_newest_ccd_school_csv_zip(school_links)
    if best_school:
        rows.append(
            {
                "source": "NCES/CCD",
                "category": "enrollment",
                "dataset_title": "CCD Public School Universe",
                "format": "ZIP",
                "url": best_school,
                "description": "NCES CCD Public School Universe (national CSV zip)",
            }
        )

    best_state = pick_newest_state_nonfiscal_zip(state_links)
    if best_state:
        rows.append(
            {
                "source": "NCES/CCD",
                "category": "enrollment",
                "dataset_title": "CCD State Nonfiscal Survey",
                "format": "ZIP",
                "url": best_state,
                "description": "NCES CCD State Nonfiscal Survey (state enrollment/staff)",
            }
        )

    best_f33 = pick_newest_f33_zip(finance_links)
    if best_f33:
        rows.append(
            {
                "source": "NCES/CCD",
                "category": "financials",
                "dataset_title": "CCD School District Finance (F-33)",
                "format": "ZIP",
                "url": best_f33,
                "description": "NCES CCD district finance / F-33 (national)",
            }
        )

    return pd.DataFrame(rows)


def discover_frss_broad_k12() -> pd.DataFrame:
    return filter_edtech_downloads(pd.DataFrame(FRSS_BROAD_K12_DOWNLOADS))


def _spp_broad_category(stem: str) -> str | None:
    if _spp_stem_category(stem) is not None:
        return None  # already collected in civil-rights/ed-tech notebook
    base = stem.replace("_OA", "").replace("_oa", "")
    if base in SPP_BROAD_K12_STEMS or stem in SPP_BROAD_K12_STEMS:
        mapping = {
            "Staffing": "teachers",
            "StaffVac": "teachers",
            "staffing": "teachers",
            "SchoolFac": "financials",
            "PhysEd": "other",
            "CCReadiness": "test_scores",
            "Assessment": "test_scores",
            "civics": "test_scores",
            "Arts": "other",
            "AfterSchoolPrograms": "other",
            "FamilyEngagement": "other",
            "FoodServices": "financials",
            "SummerPrograms": "other",
            "Tutoring": "other",
            "Transportation": "other",
            "Housing": "other",
        }
        return mapping.get(base, "other")
    return None


def discover_spp_broad_k12() -> pd.DataFrame:
    """SPP topic files for enrollment, staffing, facilities, college readiness."""
    response = requests.get(SPP_APP_JS_URL, headers=DEFAULT_HEADERS, timeout=60)
    response.raise_for_status()
    paths = sorted(set(re.findall(r"docs/release/[^\s\"'<>]+\.xlsx", response.text, re.I)))
    rows = []
    seen: set[str] = set()
    for rel in paths:
        stem = Path(rel).stem
        category = _spp_broad_category(stem)
        if category is None:
            continue
        url = f"{SPP_BASE_URL}{rel}"
        if url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "source": "NCES/SPP",
                "category": category,
                "dataset_title": f"School Pulse Panel — {stem}",
                "format": "XLSX",
                "url": url,
                "description": f"SPP (K-12 broad): {stem} — national school survey estimates",
                "dest_filename": safe_filename(Path(rel).name),
            }
        )
    return pd.DataFrame(rows)


def catalog_crdc_extracted(extract_root: Path) -> pd.DataFrame:
    """Summarize files already extracted under crdc_extracted/ by category."""
    from federal_collect import guess_category

    rows = []
    if not extract_root.exists():
        return pd.DataFrame(rows)
    for path in sorted(extract_root.rglob("*")):
        if not path.is_file():
            continue
        cat = guess_category(path.name)
        rows.append(
            {
                "file": path.name,
                "category": cat,
                "year": path.parent.name,
                "bytes": path.stat().st_size,
            }
        )
    return pd.DataFrame(rows)


def download_catalog_rows(
    catalog: pd.DataFrame,
    project_root: Path,
    federal_root: Path,
    spp_root: Path,
    download_log: Path,
) -> list[dict]:
    records = []
    for _, row in catalog.iterrows():
        category = str(row.get("category", "other"))
        source = str(row.get("source", ""))
        if source.startswith("NCES/SPP"):
            dest_root = spp_root / "broad_k12" / category
        else:
            dest_root = federal_root / category
        fname = row.get("dest_filename") or edtech_dest_filename(row)
        dest_path = dest_root / fname
        record = download_to_path(
            row["url"],
            dest_path,
            description=row["description"],
            category=category,
            download_log=download_log,
            project_root=project_root,
        )
        records.append(record)
    return records
