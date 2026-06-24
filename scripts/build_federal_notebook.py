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

**Focus areas:**
1. **Civil Rights Data Collection (CRDC)** — expand beyond 2017–18
2. **Technology in schools** — internet, devices, digital learning

**Prerequisite:** Run `collect_education_data.ipynb` first. This notebook **adds** federal files to the same `logs/manifest.csv`.

Run cells **top to bottom** (Phases 1 → 7)."""
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
    crdc_api_dest_filename,
    discover_crdc_api_files,
    discover_edtech_files,
    discover_federal_expansion_downloads,
    download_to_path,
    edtech_dest_filename,
    ensure_federal_layout,
    extract_crdc_zips,
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
print("Ed-tech folder:", PATHS["edtech_root"].resolve())
print("CRDC extracted:", PATHS["crdc_extracted_root"].resolve())
print("SPP folder:", PATHS["spp_root"].resolve())"""
)

md(
    """---
## Phase 1 — Download CRDC public-use zip bundles (national)

| Year | Approx. size | Default |
|------|-------------|---------|
| 2015–16 | ~31 MB | Yes |
| 2017–18 | ~114 MB | Skip if from first notebook |
| 2020–21 | ~78 MB | Yes |
| 2021–22 | ~800 MB | Optional (or use Phase 7 / `--with-crdc-2122`) |"""
)

code(
    """SKIP_YEARS_ALREADY_PRESENT = True
DOWNLOAD_2017_18 = False
DOWNLOAD_2021_22 = False

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
    print(f"Downloading {year} CRDC zip...")
    record = download_to_path(
        item["url"], dest, description=f"CRDC public-use zip {year}",
        category="discipline", download_log=DOWNLOAD_LOG, project_root=PROJECT_ROOT, timeout_seconds=900,
    )
    phase1_records.append(record)
    print(f"  -> {record['status']}")

print("Phase 1 done.")"""
)

md("---\n## Phase 2 — Inventory CRDC topics (incl. technology)")

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

md("---\n## Phase 3 — CRDC spreadsheets from data.ed.gov (optional; many URLs may fail)")

code(
    """crdc_api_df = discover_crdc_api_files()
print(f"CRDC API file links found: {len(crdc_api_df)}")
crdc_api_df.to_csv(FEDERAL_DISCOVERED, index=False)
crdc_api_df.head(10)"""
)

code(
    """TARGET_API_YEARS = ("2015-16", "2015-2016", "2020-21", "2020-2021")
api_records = []
for _, row in crdc_api_df.iterrows():
    blob = f"{row.get('year_hint', '')} {row['dataset_title']} {row['url']}"
    if not any(y in blob for y in TARGET_API_YEARS):
        continue
    fname = crdc_api_dest_filename(row)
    dest_path = PATHS["federal_root"] / row["category"] / fname
    record = download_to_path(
        row["url"], dest_path, description=row["description"], category=row["category"],
        download_log=DOWNLOAD_LOG, project_root=PROJECT_ROOT,
    )
    api_records.append(record)

print(f"Attempted: {len(api_records)} | downloaded: {sum(1 for r in api_records if r['status']=='downloaded')}")"""
)

md("---\n## Phase 4 — NCES / ED ed-tech survey downloads")

code("""edtech_df = discover_edtech_files()
print(f"Ed-tech file links found: {len(edtech_df)}")
edtech_df.head(10)""")

code(
    """edtech_records = []
for i, row in edtech_df.iterrows():
    dest_path = PATHS["edtech_root"] / edtech_dest_filename(row)
    record = download_to_path(
        row["url"], dest_path, description=row["description"], category="other",
        download_log=DOWNLOAD_LOG, project_root=PROJECT_ROOT,
    )
    edtech_records.append(record)
print(f"Attempted: {len(edtech_records)} | downloaded: {sum(1 for r in edtech_records if r['status']=='downloaded')}")"""
)

md("---\n## Phase 5 — Refresh manifest & summary")

code(
    """if "PATHS" not in globals():
    raise NameError("Run Step 0 first.")

manifest = refresh_manifest(DOWNLOAD_LOG, MANIFEST_CSV)
fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

summary_rows = [
    {"location": "data/raw/federal/crdc/", "files": sum(1 for p in PATHS["crdc_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/crdc_extracted/", "files": sum(1 for p in PATHS["crdc_extracted_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/edtech/", "files": sum(1 for p in PATHS["edtech_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/spp/", "files": sum(1 for p in PATHS["spp_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/ (all)", "files": sum(1 for p in PATHS["federal_root"].rglob("*") if p.is_file())},
]
print(pd.DataFrame(summary_rows).to_string(index=False))
if not fed.empty:
    print(fed.groupby("category").size())
print(f"Manifest: {MANIFEST_CSV}")"""
)

md(
    """---
## Phase 6 — Extract CRDC zips + new FRSS surveys

Unpacks CRDC topic CSVs locally. Downloads FRSS 106, 109, 110 from direct NCES URLs.

**Alternative:** `python scripts/run_federal_expansion.py`"""
)

code(
    """extract_records = extract_crdc_zips(PROJECT_ROOT, PATHS["crdc_extracted_root"], DOWNLOAD_LOG)
print(f"CRDC extract: {sum(1 for r in extract_records if r['status']=='extracted')} new")

expansion_df = discover_federal_expansion_downloads()
for _, row in expansion_df.iterrows():
    cat = str(row.get("category", "other"))
    root = PATHS["edtech_root"] if cat == "other" else PATHS["federal_root"] / cat
    download_to_path(row["url"], root / edtech_dest_filename(row), row["description"], category=cat,
                     download_log=DOWNLOAD_LOG, project_root=PROJECT_ROOT)
print("Phase 6 done — re-run Phase 5 for summary.")"""
)

md(
    """---
## Phase 7 — School Pulse Panel + optional 2021–22 CRDC

Run in terminal:

```bash
python scripts/run_federal_wave2.py
python scripts/run_federal_wave2.py --with-crdc-2122
python scripts/generate_docs.py
```

Then re-run **Phase 5**."""
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
print(f"Wrote {out} ({len(cells)} cells)")
