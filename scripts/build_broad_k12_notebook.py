"""Generate notebooks/collect_federal_broad_k12.ipynb."""

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
    """# EOQ Lab — Broader National K-12 Data Collection

**Scope:** National U.S. public education data **beyond** civil rights and ed-tech.

**Themes in this notebook:**
- Enrollment & demographics (NCES CCD)
- District finance (NCES F-33)
- Staffing & facilities (School Pulse Panel, FRSS)
- College readiness & programs (SPP, FRSS)
- CRDC topic inventory (enrollment, AP, graduation — already extracted)

**Prerequisite:** Run `collect_federal_crdc_edtech.ipynb` first (CRDC zips on disk).

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

from federal_collect import ensure_federal_layout, extract_crdc_zips, refresh_manifest
from broad_k12_collect import (
    catalog_crdc_extracted,
    discover_frss_broad_k12,
    discover_nces_ccd_downloads,
    discover_spp_broad_k12,
    download_catalog_rows,
)

PATHS = ensure_federal_layout(PROJECT_ROOT)
DOWNLOAD_LOG = PATHS["logs_dir"] / "download_log.jsonl"
MANIFEST_CSV = PATHS["logs_dir"] / "manifest.csv"
BROAD_DISCOVERED = PATHS["logs_dir"] / "federal_broad_k12_discovered.csv"

print("Project root:", PROJECT_ROOT.resolve())
print("Federal root:", PATHS["federal_root"].resolve())
print("CRDC extracted:", PATHS["crdc_extracted_root"].resolve())
print("SPP broad:", (PATHS["spp_root"] / "broad_k12").resolve())"""
)

md(
    """---
## Phase 1 — Catalog CRDC extracts (enrollment, AP, graduation, …)

Lists topic CSVs already unpacked from CRDC zips into `data/raw/federal/crdc_extracted/`.
No download — inventory only."""
)

code(
    """crdc_catalog = catalog_crdc_extracted(PATHS["crdc_extracted_root"])
if crdc_catalog.empty:
    print("No CRDC extracts found. Run collect_federal_crdc_edtech.ipynb Phase 6 first.")
else:
    print(f"CRDC extracted files: {len(crdc_catalog)}")
    print("\\nBy category:")
    print(crdc_catalog.groupby("category").size())
    print("\\nBy year:")
    print(crdc_catalog.groupby("year").size())
    display(crdc_catalog.groupby(["year", "category"]).size().unstack(fill_value=0))
    crdc_catalog.head(15)"""
)

md(
    """---
## Phase 2 — Refresh CRDC extracts (if you added new zips)

Re-unpacks any CRDC zips on disk. Skips files already extracted."""
)

code(
    """extract_records = extract_crdc_zips(
    PROJECT_ROOT,
    PATHS["crdc_extracted_root"],
    DOWNLOAD_LOG,
)
print(
    f"new: {sum(1 for r in extract_records if r['status']=='extracted')}, "
    f"skipped: {sum(1 for r in extract_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in extract_records if r['status']=='failed')}"
)"""
)

md(
    """---
## Phase 3 — NCES Common Core of Data (CCD)

Discovers newest **school universe**, **state nonfiscal**, and **district finance (F-33)** zips from NCES catalog pages."""
)

code(
    """ccd_df = discover_nces_ccd_downloads()
print(f"NCES CCD downloads queued: {len(ccd_df)}")
ccd_df"""
)

code(
    """ccd_records = download_catalog_rows(
    ccd_df, PROJECT_ROOT, PATHS["federal_root"], PATHS["spp_root"], DOWNLOAD_LOG
)
print(f"downloaded: {sum(1 for r in ccd_records if r['status']=='downloaded')}, "
      f"skipped: {sum(1 for r in ccd_records if r['status']=='skipped_exists')}, "
      f"failed: {sum(1 for r in ccd_records if r['status']=='failed')}")"""
)

md(
    """---
## Phase 4 — FRSS surveys (facilities, dual credit, English learners)

Direct NCES downloads — stable URLs."""
)

code(
    """frss_df = discover_frss_broad_k12()
frss_records = download_catalog_rows(
    frss_df, PROJECT_ROOT, PATHS["federal_root"], PATHS["spp_root"], DOWNLOAD_LOG
)
print(f"FRSS — downloaded: {sum(1 for r in frss_records if r['status']=='downloaded')}, "
      f"skipped: {sum(1 for r in frss_records if r['status']=='skipped_exists')}")"""
)

md(
    """---
## Phase 5 — School Pulse Panel (staffing, facilities, college readiness)

Topics **not** already collected in the civil-rights/ed-tech notebook."""
)

code(
    """spp_df = discover_spp_broad_k12()
print(f"SPP broad K-12 files queued: {len(spp_df)}")
spp_df.head(10)"""
)

code(
    """spp_records = download_catalog_rows(
    spp_df, PROJECT_ROOT, PATHS["federal_root"], PATHS["spp_root"], DOWNLOAD_LOG
)
print(f"SPP — downloaded: {sum(1 for r in spp_records if r['status']=='downloaded')}, "
      f"skipped: {sum(1 for r in spp_records if r['status']=='skipped_exists')}, "
      f"failed: {sum(1 for r in spp_records if r['status']=='failed')}")"""
)

md("---\n## Phase 6 — Refresh manifest & summary")

code(
    """if "PATHS" not in globals():
    raise NameError("Run Step 0 first.")

manifest = refresh_manifest(DOWNLOAD_LOG, MANIFEST_CSV)
fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

summary_rows = [
    {"location": "data/raw/federal/crdc_extracted/", "files": sum(1 for p in PATHS["crdc_extracted_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/spp/broad_k12/", "files": sum(1 for p in (PATHS["spp_root"] / "broad_k12").rglob("*") if p.is_file())},
    {"location": "data/raw/federal/enrollment/", "files": sum(1 for p in (PATHS["federal_root"] / "enrollment").rglob("*") if p.is_file())},
    {"location": "data/raw/federal/financials/", "files": sum(1 for p in (PATHS["federal_root"] / "financials").rglob("*") if p.is_file())},
    {"location": "data/raw/federal/teachers/", "files": sum(1 for p in (PATHS["federal_root"] / "teachers").rglob("*") if p.is_file())},
    {"location": "data/raw/federal/ (all)", "files": sum(1 for p in PATHS["federal_root"].rglob("*") if p.is_file())},
]

print("=== Broader K-12 collection summary ===")
print(pd.DataFrame(summary_rows).to_string(index=False))

if not fed.empty:
    print("\\nFederal manifest by category:")
    print(fed.groupby("category").size())

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

out = Path(__file__).resolve().parents[1] / "notebooks" / "collect_federal_broad_k12.ipynb"
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Wrote {out} ({len(cells)} cells)")
