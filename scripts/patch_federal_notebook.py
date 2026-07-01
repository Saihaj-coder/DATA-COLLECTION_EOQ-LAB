"""Append Phase 6/7 to federal notebook and update Step 0 + Phase 5."""

import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "collect_federal_crdc_edtech.ipynb"

STEP0_CODE = """from __future__ import annotations

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
    discover_federal_expansion_downloads,
    crdc_api_dest_filename,
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

PHASE5_CODE = """# Run Step 0 first if the kernel was restarted
if "PATHS" not in globals():
    raise NameError("Run Step 0 (imports) first, then re-run this cell.")

manifest = refresh_manifest(DOWNLOAD_LOG, MANIFEST_CSV)

fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

summary_rows = [
    {"location": "data/raw/federal/crdc/", "files": sum(1 for p in PATHS["crdc_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/crdc_extracted/", "files": sum(1 for p in PATHS["crdc_extracted_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/edtech/", "files": sum(1 for p in PATHS["edtech_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/spp/", "files": sum(1 for p in PATHS["spp_root"].rglob("*") if p.is_file())},
    {"location": "data/raw/federal/ (all)", "files": sum(1 for p in PATHS["federal_root"].rglob("*") if p.is_file())},
]

print("=== Collection summary ===")
print(pd.DataFrame(summary_rows).to_string(index=False))

if not fed.empty:
    print("\\nFederal manifest rows by category:")
    print(fed.groupby("category").size())

print(f"\\nManifest refreshed: {MANIFEST_CSV}")"""

PHASE6_MD = """---
## Phase 6 — Extract CRDC zips + new FRSS surveys

Unpacks topic CSVs from CRDC zips you already downloaded (avoids flaky data.ed.gov state files).
Downloads FRSS 106, 109, 110 and older internet-access surveys from direct NCES URLs.

**Alternative:** `python scripts/run_federal_expansion.py` from the project root."""

PHASE6_CODE = """from federal_collect import discover_federal_expansion_downloads, extract_crdc_zips

extract_records = extract_crdc_zips(
    PROJECT_ROOT,
    PATHS["crdc_extracted_root"],
    DOWNLOAD_LOG,
)
print(
    f"CRDC extract — new: {sum(1 for r in extract_records if r['status']=='extracted')}, "
    f"skipped: {sum(1 for r in extract_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in extract_records if r['status']=='failed')}"
)

expansion_df = discover_federal_expansion_downloads()
expansion_records = []
for _, row in expansion_df.iterrows():
    category = str(row.get("category", "other"))
    dest_root = PATHS["edtech_root"] if category == "other" else PATHS["federal_root"] / category
    dest_path = dest_root / edtech_dest_filename(row)
    record = download_to_path(
        row["url"],
        dest_path,
        description=row["description"],
        category=category,
        download_log=DOWNLOAD_LOG,
        project_root=PROJECT_ROOT,
    )
    expansion_records.append(record)

print(
    f"FRSS expansion — downloaded: {sum(1 for r in expansion_records if r['status']=='downloaded')}, "
    f"skipped: {sum(1 for r in expansion_records if r['status']=='skipped_exists')}, "
    f"failed: {sum(1 for r in expansion_records if r['status']=='failed')}"
)"""

PHASE7_MD = """---
## Phase 7 — School Pulse Panel + optional 2021–22 CRDC

**Civil rights SPP:** Absenteeism, Behavior, CrimeSafety, MentalHealth, SocialEmotional, …  
**Ed-tech SPP:** Technology, LearningMode, SupplyChain

Run in terminal (recommended):

```bash
python scripts/run_federal_wave2.py
python scripts/run_federal_wave2.py --with-crdc-2122
python scripts/generate_docs.py
```

Then re-run **Phase 5** above to refresh the summary."""


def to_source(text: str) -> list[str]:
    return [line + "\n" for line in text.split("\n")]


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": to_source(text)}


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": to_source(text),
    }


nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
cells = nb["cells"]

# Update Step 0 code (first code cell after Step 0 markdown)
for i, cell in enumerate(cells):
    if cell["cell_type"] == "markdown" and "Step 0" in "".join(cell.get("source", [])):
        if i + 1 < len(cells) and cells[i + 1]["cell_type"] == "code":
            cells[i + 1]["source"] = to_source(STEP0_CODE)
        break

# Update Phase 5 code (last code cell or cell after Phase 5 markdown)
for i, cell in enumerate(cells):
    if cell["cell_type"] == "markdown" and "Phase 5" in "".join(cell.get("source", [])):
        if i + 1 < len(cells) and cells[i + 1]["cell_type"] == "code":
            cells[i + 1]["source"] = to_source(PHASE5_CODE)
        break

# Fix Phase 4 download to use edtech_dest_filename if needed
for cell in cells:
    src = "".join(cell.get("source", []))
    if "edtech_records = []" in src and "edtech_dest_filename" not in src:
        cell["source"] = to_source(src.replace(
            "dest_path = PATHS[\"edtech_root\"] / Path(row[\"url\"]).name",
            "dest_path = PATHS[\"edtech_root\"] / edtech_dest_filename(row)",
        ))

# Remove any existing Phase 6/7 cells (idempotent)
cells = [
    c
    for c in cells
    if not any(
        p in "".join(c.get("source", []))
        for p in ("Phase 6", "Phase 7", "discover_federal_expansion_downloads", "run_federal_wave2")
    )
]

cells.extend([md_cell(PHASE6_MD), code_cell(PHASE6_CODE), md_cell(PHASE7_MD)])

nb["cells"] = cells
NOTEBOOK.write_text(json.dumps(nb, indent=1), encoding="utf-8")

print(f"Fixed notebook: {len(cells)} cells")
for i, c in enumerate(cells):
    preview = "".join(c.get("source", []))[:72].replace("\n", " ")
    print(f"  {i:2} {c['cell_type'][:4]} | {preview}")
