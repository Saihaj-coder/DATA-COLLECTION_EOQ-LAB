"""Generate notebooks/collect_state_colorado_texas.ipynb."""

import json
from pathlib import Path

cells: list[dict] = []


def md(text: str) -> None:
    cells.append(
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.split("\n")],
        }
    )


def code(text: str) -> None:
    cells.append(
        {
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in text.split("\n")],
        }
    )


md(
    """# EOQ Lab — Colorado & Texas Public Education Data Collection (max mode)

**States:** Colorado, Texas  
**Goal:** Download as much publicly available K–12 education data as practical into `data/raw/{state}/`, and cut **state-only rows** from existing national (federal) data into `data/cleaned/{state}/`.

**How this differs from Hawaii/Virginia:**
- Virginia used a **CKAN** API (`data.virginia.gov`).
- Colorado and Texas use **Socrata** open data APIs (`data.colorado.gov`, `data.texas.gov`) plus **BeautifulSoup** scraping of state DOE pages.

**Prerequisites:** Federal notebooks should already have run (NCES CCD school zip + CRDC extracts in `data/raw/federal/`). Phase 7 reuses those files.

**Run order:** **Step 0.2** → Phases 1–8, **one cell at a time** (Shift+Enter). This notebook does not auto-run.

**Packages:** Install via terminal (`py -3 -m pip install -r requirements.txt`) — see Step 0.1. Do not use `%pip` here."""
)

md(
    """---
## Step 0.1 — Packages *(run once in a terminal — not in this notebook)*

**Do not run `%pip` in this notebook** — it can hang the kernel on Windows and make the notebook feel "out of control."

In a **terminal** (project root), if needed:

```bash
py -3 -m pip install -r requirements.txt
```

Then open this notebook and start at **Step 0.2** below."""
)

md(
    """---
## Step 0.2 — Project paths & imports

Sets `PROJECT_ROOT`, creates `data/raw/colorado/`, `data/raw/texas/`, and matching `data/cleaned/` folders.

**Max-collection settings** (tune here before running later phases):"""
)

code(
    """from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Find project root (works when cwd is project root or notebooks/)
PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent
elif not (PROJECT_ROOT / "data").exists() and (PROJECT_ROOT.parent / "data").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from federal_collect import refresh_manifest
from state_collect import (
    STATE_ABBRS,
    STATE_SLUGS,
    discover_html_seed_pages,
    discover_socrata_datasets,
    direct_download_catalog,
    download_state_rows,
    ensure_state_layout,
    filter_crdc_extracted_for_state,
    filter_nces_ccd_for_state,
    filter_nces_f33_for_state,
    state_collection_summary,
)
import colorado_collect
import texas_collect

PATHS = ensure_state_layout(PROJECT_ROOT, STATE_SLUGS)
DOWNLOAD_LOG = PATHS["logs_dir"] / "download_log.jsonl"
MANIFEST_CSV = PATHS["logs_dir"] / "manifest.csv"

CO_DISCOVERED = PATHS["logs_dir"] / "co_discovered_links.csv"
TX_DISCOVERED = PATHS["logs_dir"] / "tx_discovered_links.csv"
TX_ARCGIS_DISCOVERED = PATHS["logs_dir"] / "tx_arcgis_discovered.csv"

# Pause between bulk downloads (seconds) — polite to state servers
SECONDS_BETWEEN_DOWNLOADS = 0.5

# Texas PEIMS single-file page lists 80+ ZIPs; 0 = download all years (very large)
MAX_TX_PEIMS_ZIP_DOWNLOADS = 0

# Socrata: skip map/story views that 404 on CSV export (recommended)
SOCRATA_EXPORTABLE_ONLY = True
SOCRATA_MAX_PER_QUERY = 200
SECONDS_BETWEEN_SOCRATA_CHECKS = 0.3

# Texas ArcGIS: download CSV layers after cataloging (Phase 6b)
DOWNLOAD_ARCGIS_CSV = True

print("Project root:", PROJECT_ROOT.resolve())
print("States:", list(STATE_SLUGS))
print("Download log:", DOWNLOAD_LOG.resolve())
print("Max mode: PEIMS cap =", MAX_TX_PEIMS_ZIP_DOWNLOADS, "| Socrata exportable only =", SOCRATA_EXPORTABLE_ONLY)"""
)

md(
    """---
## Phase 1 — Direct downloads

Hand-picked stable CDE/TEA URLs before automated discovery. Files land in `data/raw/{state}/{category}/`."""
)

code(
    """phase1_catalog = pd.concat(
    [
        direct_download_catalog("colorado", colorado_collect.DIRECT_DOWNLOADS),
        direct_download_catalog("texas", texas_collect.DIRECT_DOWNLOADS),
    ],
    ignore_index=True,
)
print(f"Phase 1 URLs queued: {len(phase1_catalog)}")
phase1_catalog"""
)

code(
    """phase1_records = download_state_rows(
    phase1_catalog,
    PROJECT_ROOT,
    DOWNLOAD_LOG,
    seconds_between=SECONDS_BETWEEN_DOWNLOADS,
)
print(
    f"downloaded: {sum(1 for r in phase1_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in phase1_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in phase1_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 2 — Colorado open data (Socrata API)

**Portal:** [data.colorado.gov](https://data.colorado.gov)  
**Method:** Socrata catalog API. Tabular datasets export as CSV; map-only views are skipped when `SOCRATA_EXPORTABLE_ONLY` is True.

If you see **429 Too Many Requests**, wait 1–2 minutes, **restart the kernel**, re-run Step 0.2, and retry this cell (the script retries with backoff).

Discovered links are saved to `logs/co_discovered_links.csv` before download."""
)

code(
    """co_socrata_df = discover_socrata_datasets(
    colorado_collect.SOCRATA_BASE,
    colorado_collect.SOCRATA_SEARCH_QUERIES,
    "colorado",
    attribution_keywords=colorado_collect.SOCRATA_ATTRIBUTION_KEYWORDS,
    max_per_query=SOCRATA_MAX_PER_QUERY,
    exportable_only=SOCRATA_EXPORTABLE_ONLY,
    seconds_between_checks=SECONDS_BETWEEN_SOCRATA_CHECKS,
)
co_socrata_df.to_csv(CO_DISCOVERED, index=False)
print(f"Colorado Socrata datasets discovered (exportable): {len(co_socrata_df)}")
print("Saved:", CO_DISCOVERED)
co_socrata_df.head(10)"""
)

code(
    """co_socrata_records = download_state_rows(
    co_socrata_df,
    PROJECT_ROOT,
    DOWNLOAD_LOG,
    seconds_between=SECONDS_BETWEEN_DOWNLOADS,
)
print(
    f"CO Socrata — downloaded: {sum(1 for r in co_socrata_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in co_socrata_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in co_socrata_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 3 — Texas open data (Socrata API)

**Portal:** [data.texas.gov](https://data.texas.gov)  
Same Socrata pattern as Colorado, filtered to Texas Education Agency datasets."""
)

code(
    """tx_socrata_df = discover_socrata_datasets(
    texas_collect.SOCRATA_BASE,
    texas_collect.SOCRATA_SEARCH_QUERIES,
    "texas",
    attribution_keywords=texas_collect.SOCRATA_ATTRIBUTION_KEYWORDS,
    max_per_query=SOCRATA_MAX_PER_QUERY,
    exportable_only=SOCRATA_EXPORTABLE_ONLY,
    seconds_between_checks=SECONDS_BETWEEN_SOCRATA_CHECKS,
)
tx_socrata_df.to_csv(TX_DISCOVERED, index=False)
print(f"Texas Socrata datasets discovered (exportable): {len(tx_socrata_df)}")
tx_socrata_df.head(10)"""
)

code(
    """tx_socrata_records = download_state_rows(
    tx_socrata_df,
    PROJECT_ROOT,
    DOWNLOAD_LOG,
    seconds_between=SECONDS_BETWEEN_DOWNLOADS,
)
print(
    f"TX Socrata — downloaded: {sum(1 for r in tx_socrata_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in tx_socrata_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in tx_socrata_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 4 — Colorado CDE pages (BeautifulSoup)

Scrapes **direct file links** from Colorado Department of Education index pages (accountability, CMAS, PSAT, etc.).

CDE uses `/fs/resource-manager/view/{uuid}` links with a `data-file-name` attribute."""
)

code(
    """co_html_df = discover_html_seed_pages(
    colorado_collect.HTML_SEED_URLS,
    "colorado",
    page_label="CDE",
)
print(f"Colorado HTML links discovered: {len(co_html_df)}")
co_html_df.head(10)"""
)

code(
    """co_html_records = download_state_rows(
    co_html_df,
    PROJECT_ROOT,
    DOWNLOAD_LOG,
    seconds_between=SECONDS_BETWEEN_DOWNLOADS,
)
print(
    f"CO HTML — downloaded: {sum(1 for r in co_html_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in co_html_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in co_html_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 5 — Texas TEA pages (BeautifulSoup)

Scrapes file links from Texas Education Agency report hubs (PEIMS finance, assessments, SAT/ACT, graduation, educator data, etc.).

**Note:** `MAX_TX_PEIMS_ZIP_DOWNLOADS = 0` downloads **every** PEIMS single-file ZIP on that page (many GB). Set to e.g. `6` for only the newest six years."""
)

code(
    """tx_html_df = discover_html_seed_pages(
    texas_collect.HTML_SEED_URLS,
    "texas",
    page_label="TEA",
)
before = len(tx_html_df)
tx_html_df = texas_collect.limit_texas_peims_downloads(tx_html_df, MAX_TX_PEIMS_ZIP_DOWNLOADS)
print(f"Texas HTML links discovered: {before} (downloading {len(tx_html_df)} after PEIMS cap)")
tx_html_df.head(10)"""
)

code(
    """tx_html_records = download_state_rows(
    tx_html_df,
    PROJECT_ROOT,
    DOWNLOAD_LOG,
    seconds_between=SECONDS_BETWEEN_DOWNLOADS,
)
print(
    f"TX HTML — downloaded: {sum(1 for r in tx_html_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in tx_html_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in tx_html_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 6a — Texas ArcGIS open data (catalog)

**Portal:** [TEA Public Open Data on ArcGIS](https://schoolsdata2-tea-texas.opendata.arcgis.com/)

Catalogs datasets via the ArcGIS Search API → `logs/tx_arcgis_discovered.csv`."""
)

code(
    """tx_arcgis_df = texas_collect.discover_tea_arcgis_items(max_items=200)
tx_arcgis_df.to_csv(TX_ARCGIS_DISCOVERED, index=False)
print(f"Texas ArcGIS items cataloged: {len(tx_arcgis_df)}")
tx_arcgis_df.head(10)"""
)

md(
    """---
## Phase 6b — Texas ArcGIS CSV downloads

Resolves ArcGIS Online item metadata and downloads CSV layers via the `/data` endpoint (Hub bulk exports often fail)."""
)

code(
    """if DOWNLOAD_ARCGIS_CSV:
    tx_arcgis_catalog = texas_collect.build_arcgis_download_catalog(tx_arcgis_df)
    print(f"ArcGIS CSV layers queued: {len(tx_arcgis_catalog)}")
    tx_arcgis_records = download_state_rows(
        tx_arcgis_catalog,
        PROJECT_ROOT,
        DOWNLOAD_LOG,
        seconds_between=SECONDS_BETWEEN_DOWNLOADS,
    )
    print(
        f"TX ArcGIS — downloaded: {sum(1 for r in tx_arcgis_records if r['status']=='downloaded')}, "
        f"skipped: {sum(1 for r in tx_arcgis_records if r['status']=='skipped_exists')}, "
        f"failed: {sum(1 for r in tx_arcgis_records if r['status']=='failed')}"
    )
else:
    print("Skipped ArcGIS downloads (DOWNLOAD_ARCGIS_CSV = False)")"""
)

md(
    """---
## Phase 7 — Federal data filtered to Colorado & Texas

Reuses **national files already on disk** (no re-download of full CRDC zips):

1. **NCES CCD** school universe → filter `ST == 'CO'` or `'TX'` → `data/cleaned/{state}/enrollment/`
2. **NCES F-33** district finance (if `Sdf*_1a.zip` on disk) → `data/cleaned/{state}/financials/`
3. **CRDC extracted CSVs** → filter `LEA_STATE` → `data/cleaned/{state}/{category}/`

Phase 7 may take several minutes for Texas (large row counts)."""
)

code(
    """federal_filter_summary = []

for state_slug in STATE_SLUGS:
    abbr = STATE_ABBRS[state_slug]
    print(f"\\n=== {state_slug.title()} ({abbr}) federal filter ===")

    nces_result = filter_nces_ccd_for_state(PROJECT_ROOT, state_slug, abbr, DOWNLOAD_LOG)
    print("NCES CCD schools:", nces_result)

    f33_result = filter_nces_f33_for_state(PROJECT_ROOT, state_slug, abbr, DOWNLOAD_LOG)
    print("NCES F-33 districts:", f33_result)

    crdc_written = filter_crdc_extracted_for_state(PROJECT_ROOT, state_slug, abbr, DOWNLOAD_LOG)
    n_written = sum(1 for r in crdc_written if r.get("status") == "written")
    n_skip = sum(1 for r in crdc_written if r.get("status") == "skipped_exists")
    print(f"CRDC extracts: {n_written} written, {n_skip} skipped (already on disk)")

    federal_filter_summary.append(
        {"state": state_slug, "nces": nces_result, "f33": f33_result, "crdc_files": n_written}
    )

pd.DataFrame(federal_filter_summary)"""
)

md(
    """---
## Phase 8 — Manifest refresh & summary

Rebuilds `logs/manifest.csv` and prints file counts per state (raw + cleaned)."""
)

code(
    """manifest = refresh_manifest(DOWNLOAD_LOG, MANIFEST_CSV)

for state_slug in STATE_SLUGS:
    print(f"\\n=== {state_slug.upper()} collection summary ===")
    summary = state_collection_summary(PROJECT_ROOT, state_slug)
    if summary.empty:
        print("(no files yet)")
    else:
        print(summary.to_string(index=False))

state_rows = manifest[manifest["state"].isin(STATE_SLUGS)] if not manifest.empty else pd.DataFrame()
if not state_rows.empty:
    print("\\nManifest rows by state:")
    print(state_rows.groupby(["state", "category"]).size())

print(f"\\nManifest: {MANIFEST_CSV}")
print("Regenerate docs: python scripts/generate_docs.py")"""
)

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "cells": cells,
}

out = Path(__file__).resolve().parents[1] / "notebooks" / "collect_state_colorado_texas.ipynb"
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Wrote {out} ({len(cells)} cells)")
