"""Texas-specific discovery seeds and Socrata configuration."""

from __future__ import annotations

import re

import pandas as pd

SOCRATA_BASE = "https://data.texas.gov"

SOCRATA_SEARCH_QUERIES = [
    "Texas Education Agency",
    "TEA",
    "PEIMS",
    "STAAR",
    "accountability",
    "school district",
    "graduation",
    "discipline",
    "educator",
    "enrollment",
]

SOCRATA_ATTRIBUTION_KEYWORDS = (
    "Texas Education Agency",
    "TEA",
    "Research and Analysis",
)

# TEA report hubs — harvest direct file links
HTML_SEED_URLS = [
    "https://tea.texas.gov/finance-and-grants/state-funding/state-funding-reports-and-data/peims-financial-data-downloads",
    "https://tea.texas.gov/finance-and-grants/state-funding/state-funding-reports-and-data/peims-single-file-financial-data-downloads",
    "https://tea.texas.gov/finance-and-grants/state-funding/state-funding-reports-and-data/peims-multiple-file-financial-data-downloads",
    "https://tea.texas.gov/data-reports/data-and-reports",
    "https://tea.texas.gov/data-reports/student-assessment-results/data-file-formats",
    "https://tea.texas.gov/data-reports/school-performance/accountability-research/satact/sat-and-act-data-search-and-data-downloads",
    "https://tea.texas.gov/data-reports/educator-data",
    "https://tea.texas.gov/data-reports/school-performance/accountability-research/completion-graduation-and-dropout/completion-graduation-and-dropout",
]

# Known high-value direct downloads (smaller summarized workbook first)
DIRECT_DOWNLOADS = [
    {
        "dataset_title": "PEIMS Financial Data Dictionary",
        "url": "https://tea.texas.gov/sites/default/files/PEIMS-Financial-Data-Dictionary.pdf",
        "description": "Texas: PEIMS financial data dictionary (documentation)",
        "category": "financials",
        "format": "PDF",
    },
]

# Texas ArcGIS open data (optional Phase 4 — catalog API base)
TEA_ARCGIS_PORTAL = "https://schoolsdata2-tea-texas.opendata.arcgis.com"
TEA_ARCGIS_ITEMS_API = (
    f"{TEA_ARCGIS_PORTAL}/api/search/v1/collections/dataset/items"
)

# Cap PEIMS single-file zip downloads (each can be 7–26 MB; many years on one page)
# Set to 0 in the notebook for maximum collection (all PEIMS years — very large).
DEFAULT_MAX_PEIMS_ZIP_DOWNLOADS = 0

ARCGIS_ITEM_API = "https://www.arcgis.com/sharing/rest/content/items"


def limit_texas_peims_downloads(catalog: pd.DataFrame, max_recent: int = DEFAULT_MAX_PEIMS_ZIP_DOWNLOADS) -> pd.DataFrame:
    """
    Limit ZIP files harvested from the PEIMS single-file page to the newest N years.

    Set max_recent=0 in the notebook to download every link (large).
    """
    if catalog.empty or max_recent <= 0:
        return catalog
    peims = catalog[catalog["url"].astype(str).str.contains(".zip", case=False, na=False)].copy()
    if peims.empty:
        return catalog
    other = catalog[~catalog.index.isin(peims.index)]

    def year_key(title: str) -> int:
        match = re.search(r"20\d{2}", str(title))
        return int(match.group()) if match else 0

    peims = peims.assign(_year=peims["dataset_title"].map(year_key))
    peims = peims.sort_values("_year", ascending=False).head(max_recent).drop(columns="_year")
    return pd.concat([other, peims], ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)


def discover_tea_arcgis_items(max_items: int = 200) -> pd.DataFrame:
    """Inventory datasets on TEA's ArcGIS open data portal."""
    import requests

    from federal_collect import DEFAULT_HEADERS, safe_filename
    from state_collect import guess_category

    rows: list[dict] = []
    # ArcGIS Search API accepts `limit` only (no offset — returns 400)
    response = requests.get(
        TEA_ARCGIS_ITEMS_API,
        params={"limit": min(max_items, 50)},
        headers=DEFAULT_HEADERS,
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features") or []
    for feature in features:
        props = feature.get("properties") or {}
        title = props.get("title") or props.get("name") or feature.get("id")
        item_id = feature.get("id") or props.get("id")
        if not item_id:
            continue
        rows.append(
            {
                "state": "texas",
                "source": "ArcGIS",
                "dataset_id": item_id,
                "dataset_title": title,
                "description": f"Texas TEA ArcGIS open data: {title}",
                "category": guess_category(str(title)),
                "url": f"{TEA_ARCGIS_PORTAL}/datasets/{item_id}",
                "dest_filename": "",
                "format": props.get("type", "dataset"),
            }
        )
        if len(rows) >= max_items:
            break
    return pd.DataFrame(rows)


def build_arcgis_download_catalog(arcgis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve ArcGIS Online item metadata into direct /data download URLs.

    TEA's Hub export jobs often fail; item data URLs usually work for CSV layers.
    """
    import requests

    from federal_collect import DEFAULT_HEADERS, safe_filename

    if arcgis_df.empty:
        return arcgis_df

    rows: list[dict] = []
    for _, row in arcgis_df.iterrows():
        item_id = str(row.get("dataset_id") or "")
        if not item_id:
            continue
        meta = requests.get(
            f"{ARCGIS_ITEM_API}/{item_id}",
            params={"f": "json"},
            headers=DEFAULT_HEADERS,
            timeout=60,
        )
        if not meta.ok:
            continue
        info = meta.json()
        item_type = (info.get("type") or "").upper()
        if item_type not in {"CSV", "CSV COLLECTION"}:
            continue
        name = info.get("name") or f"arcgis_{item_id}"
        if item_type == "CSV COLLECTION":
            dest = safe_filename(name if name.lower().endswith(".zip") else f"{name}.zip")
            file_format = "ZIP"
        else:
            dest = safe_filename(name if name.lower().endswith(".csv") else f"{name}.csv")
            file_format = "CSV"
        rows.append(
            {
                "state": "texas",
                "source": "ArcGIS",
                "dataset_id": item_id,
                "dataset_title": row.get("dataset_title") or name,
                "description": row.get("description") or f"Texas TEA ArcGIS: {name}",
                "category": row.get("category") or guess_category(str(name)),
                "url": f"{ARCGIS_ITEM_API}/{item_id}/data",
                "dest_filename": dest,
                "format": file_format,
            }
        )
    return pd.DataFrame(rows)
