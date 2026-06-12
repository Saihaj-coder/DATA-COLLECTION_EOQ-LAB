"""One-off script to generate notebooks/collect_federal_crdc_edtech.ipynb."""

import json
from pathlib import Path

cells = []


def md(s: str) -> None:
    cells.append(
        {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in s.split("\n")]}
    )


def code(s: str) -> None:
    cells.append(
        {
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in s.split("\n")],
        }
    )


md(
    """# EOQ Lab — National CRDC & Ed-Tech Data Collection

**Scope:** U.S. **national** public education data (not Hawaii/Virginia state sites).

**Focus areas (Professor Keppler):**
1. **Civil Rights Data Collection (CRDC)** — expand beyond 2017–18
2. **Technology in schools** — internet, devices, digital learning

**Prerequisite:** Run `collect_education_data.ipynb` first (Phase 4 CRDC setup). This notebook **adds** new federal files and logs to the same `logs/manifest.csv`.

Run cells **top to bottom**."""
)

code("%pip install -q requests beautifulsoup4 pandas openpyxl")

md("---\n## Step 0 — Project paths & imports")

code(
    """from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent
elif not (PROJECT_ROOT / "data").exists() and (PROJECT_ROOT.parent / "data").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from federal_collect import (
    CRDC_PUBLIC_ZIPS,
    discover_crdc_api_files,
    discover_edtech_files,
    download_to_path,
    ensure_federal_layout,
    inventory_crdc_zips,
    list_crdc_zip_topics,
    refresh_manifest,
)

PATHS = ensure_federal_layout(PROJECT_ROOT)
DOWNLOAD_LOG = PATHS["logs_dir"] / "download_log.jsonl"
MANIFEST_CSV = PATHS["logs_dir"] / "manifest.csv"
FEDERAL_DISCOVERED = PATHS["logs_dir"] / "federal_phase2_discovered_links.csv"

print("Project root:", PROJECT_ROOT.resolve())
print("CRDC folder:", PATHS["crdc_root"].resolve())
print("Ed-tech folder:", PATHS["edtech_root"].resolve())"""
)

md(
    """---
## Phase 1 — Download CRDC public-use zip bundles (national)

These zips contain **all U.S. states** — school and LEA CSV files.

| Year | Approx. size | Default |
|------|-------------|---------|
| 2015–16 | ~31 MB | Yes |
| 2017–18 | ~114 MB | Skip if you already downloaded in the first notebook |
| 2020–21 | ~78 MB | Yes (newer + more tech fields) |
| 2021–22 | ~800 MB | **Optional** (set flag below) |"""
)

code(
    """# --- Phase 1 settings ---
SKIP_YEARS_ALREADY_PRESENT = True   # skip zip if file already on disk
DOWNLOAD_2017_18 = False            # you likely have this from the first notebook
DOWNLOAD_2021_22 = False            # very large; turn on only if you want the newest CRDC

YEARS_TO_DOWNLOAD = {"2015-16", "2020-21"}
if DOWNLOAD_2017_18:
    YEARS_TO_DOWNLOAD.add("2017-18")
if DOWNLOAD_2021_22:
    YEARS_TO_DOWNLOAD.add("2021-22")

phase1_records = []

for item in CRDC_PUBLIC_ZIPS:
    year = item["year"]
    if year not in YEARS_TO_DOWNLOAD:
        print(f"SKIP (not selected): {year}")
        continue

    dest = PATHS["crdc_root"] / year / item["filename"]
    if SKIP_YEARS_ALREADY_PRESENT and dest.exists() and dest.stat().st_size > 0:
        print(f"Already have: {dest.relative_to(PROJECT_ROOT)}")
        continue

    print(f"Downloading {year} CRDC zip... (may take several minutes)")
    record = download_to_path(
        item["url"],
        dest,
        description=f"CRDC public-use zip {year}",
        category="discipline",
        download_log=DOWNLOAD_LOG,
        project_root=PROJECT_ROOT,
        timeout_seconds=900,
    )
    record["local_path"] = str(dest.relative_to(PROJECT_ROOT))
    phase1_records.append(record)
    size_mb = record["bytes"] / 1024 / 1024
    print(f"  -> {record['status']}: {dest.name} ({size_mb:.1f} MB)")

if phase1_records:
    display(pd.DataFrame(phase1_records))
else:
    print("No new CRDC zips downloaded.")"""
)

md(
    """---
## Phase 2 — Inventory CRDC topics (incl. technology)

Lists every CSV topic inside each CRDC zip. Topics matching **internet / computer / device / digital / distance** are flagged."""
)

code(
    """inventory_df = inventory_crdc_zips(PATHS["crdc_root"])
display(inventory_df)

TECH_KEYS = ("internet", "wifi", "computer", "device", "technology", "digital", "distance", "broadband")

for zip_path in sorted(PATHS["crdc_root"].rglob("*-crdc-data.zip")):
    year = zip_path.parent.name
    topics = list_crdc_zip_topics(zip_path)
    tech = [t for t in topics if any(k in t.lower() for k in TECH_KEYS)]
    print(f"\\n{year}: {len(tech)} tech-related topics (of {len(topics)} total)")
    for t in tech:
        print(f"  - {t}")"""
)

md(
    """---
## Phase 3 — CRDC topic files from data.ed.gov (2015–16 & 2020–21)

The API gives **individual** CRDC spreadsheets (discipline, enrollment, etc.) — complements the zip bundles."""
)

code(
    """crdc_api_df = discover_crdc_api_files()
print(f"CRDC direct-download links (ArcGIS map links removed): {len(crdc_api_df)}")
crdc_api_df.to_csv(FEDERAL_DISCOVERED, index=False)
crdc_api_df.head(10)"""
)

code(
    """# Download CRDC API files into data/raw/federal/{category}/
# (ArcGIS map links are excluded; failed URLs are logged and skipped — loop keeps going)
TARGET_API_YEARS = ("2015-16", "2015-2016", "2020-21", "2020-2021")

api_records = []
for _, row in crdc_api_df.iterrows():
    hint = str(row.get("year_hint", ""))
    blob = f"{hint} {row['dataset_title']} {row['url']}"
    if not any(y in blob for y in TARGET_API_YEARS):
        continue

    fname = crdc_api_dest_filename(row)
    dest_path = PATHS["federal_root"] / row["category"] / fname
    print(f"[{len(api_records)+1}] {row['dataset_title'][:70]}...")
    record = download_to_path(
        row["url"],
        dest_path,
        description=row["description"],
        category=row["category"],
        download_log=DOWNLOAD_LOG,
        project_root=PROJECT_ROOT,
    )
    if record["status"] == "failed":
        print(f"  -> FAILED: {record.get('error', 'unknown')[:100]}")
    elif record["status"] == "skipped_exists":
        print(f"  -> skipped (already had file): {fname}")
    else:
        print(f"  -> downloaded: {fname}")
    record["local_path"] = str(dest_path.relative_to(PROJECT_ROOT))
    api_records.append(record)

print(f"\\nCRDC API downloads attempted: {len(api_records)}")
downloaded = sum(1 for r in api_records if r["status"] == "downloaded")
skipped = sum(1 for r in api_records if r["status"] == "skipped_exists")
failed = sum(1 for r in api_records if r["status"] == "failed")
print(f"New downloads: {downloaded}, skipped: {skipped}, failed: {failed}")"""
)

md(
    """---
## Phase 4 — NCES / ED ed-tech survey downloads

National surveys on **technology in schools**, **internet access**, and **teacher technology use**."""
)

code(
    """edtech_df = discover_edtech_files()
print(f"Ed-tech file links found: {len(edtech_df)}")
edtech_df.head(10)"""
)

code(
    """edtech_records = []
for i, row in edtech_df.iterrows():
    dest_path = PATHS["edtech_root"] / Path(row["url"]).name
    print(f"[{i+1}/{len(edtech_df)}] {row['dataset_title'][:65]}...")
    record = download_to_path(
        row["url"],
        dest_path,
        description=row["description"],
        category="other",
        download_log=DOWNLOAD_LOG,
        project_root=PROJECT_ROOT,
    )
    record["local_path"] = str(dest_path.relative_to(PROJECT_ROOT))
    edtech_records.append(record)

print(f"\\nEd-tech downloads attempted: {len(edtech_records)}")"""
)

md("---\n## Phase 5 — Refresh manifest & summary")

code(
    """manifest = refresh_manifest(DOWNLOAD_LOG, MANIFEST_CSV)

fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

summary_rows = [
    {"location": "data/raw/federal/crdc/", "files": sum(1 for p in PATHS["crdc_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/edtech/", "files": sum(1 for p in PATHS["edtech_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/ (all)", "files": sum(1 for p in PATHS["federal_root"].rglob("*") if p.is_file())},
]

print("=== Collection summary ===")
print(pd.DataFrame(summary_rows).to_string(index=False))

if not fed.empty:
    print("\\nFederal manifest rows by category:")
    print(fed.groupby("category").size())

print(f"\\nManifest refreshed: {MANIFEST_CSV}")"""
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

out = Path(__file__).resolve().parents[1] / "notebooks" / "collect_federal_crdc_edtech.ipynb"
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Wrote {out}")
