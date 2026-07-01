# EOQ Lab — Public Education Data Collection

Reproducible Python/Jupyter workflow for collecting publicly available U.S. public education data.

**State coverage:** Hawaii, Virginia, Colorado, Texas  
**Federal coverage:** CRDC, NCES CCD, FRSS, School Pulse Panel (national files; state rows extracted to `data/cleaned/`)

All downloads are logged to `logs/manifest.csv` and `logs/download_log.jsonl`.

---

## Collection snapshot (July 2026)

| State | Raw files | Cleaned files | Combined |
|-------|----------:|--------------:|---------:|
| Hawaii | 78 | 50 | 128 |
| Virginia | 220 | 50 | 270 |
| Colorado | 32 | 88 | 120 |
| Texas | 168 | 87 | 255 |
| **Four states** | **498** | **275** | **773** |

Plus **~482** national files under `data/raw/federal/`.

---

## Notebooks

Run in Cursor or Jupyter. Install dependencies once (see [Quick start](#quick-start)), then run each notebook **top to bottom** (or phase-by-phase for Colorado/Texas).

| Notebook | Purpose | Prerequisite |
|----------|---------|--------------|
| [`notebooks/collect_education_data.ipynb`](notebooks/collect_education_data.ipynb) | Hawaii + Virginia state data; baseline federal NCES/CRDC; HI/VA cleaned extracts | None |
| [`notebooks/collect_federal_crdc_edtech.ipynb`](notebooks/collect_federal_crdc_edtech.ipynb) | National CRDC (2015–16, 2020–21) + ed-tech surveys + SPP civil-rights topics | Notebook 1 recommended |
| [`notebooks/collect_federal_broad_k12.ipynb`](notebooks/collect_federal_broad_k12.ipynb) | Broader national K–12: CCD finance, FRSS, SPP staffing/facilities | Notebook 2 (CRDC zips extracted) |
| [`notebooks/collect_state_colorado_texas.ipynb`](notebooks/collect_state_colorado_texas.ipynb) | Colorado + Texas (Socrata, CDE/TEA scraping, ArcGIS) + CO/TX federal extracts | Federal data on disk recommended |

**Tips:**
- Install packages in a **terminal** (`py -3 -m pip install -r requirements.txt`) — do not use `%pip` in notebooks on Windows.
- After editing files in `scripts/`, **restart the kernel** before re-running notebook cells.
- Colorado/Texas notebook: run **one code cell at a time**; avoid **Run All** (Phase 5 can download many GB of PEIMS data).

---

## Quick start

```bash
cd "Data Collection - EOQ Lab"
py -3 -m pip install -r requirements.txt
```

Recommended order:

1. `notebooks/collect_education_data.ipynb` — Hawaii & Virginia
2. `notebooks/collect_federal_crdc_edtech.ipynb` — national CRDC + ed-tech
3. `notebooks/collect_federal_broad_k12.ipynb` — broader national K–12
4. `notebooks/collect_state_colorado_texas.ipynb` — Colorado & Texas (Step 0.2 → Phases 1–8)

Regenerate documentation after new downloads:

```bash
py -3 scripts/generate_docs.py
```

CLI alternative for Colorado/Texas (same logic as the notebook):

```bash
py -3 scripts/run_co_tx_collection.py
```

---

## Data layout

### Raw (`data/raw/`) — original downloads; do not edit by hand

| Path | Contents |
|------|----------|
| `data/raw/hawaii/` | Hawaii DOE, HIDOE, hcnf fiscal reports (~78 files) |
| `data/raw/virginia/` | Virginia Open Data / VDOE (~220 files) |
| `data/raw/colorado/` | CDE + data.colorado.gov (~32 files; test scores, enrollment, discipline) |
| `data/raw/texas/` | TEA + data.texas.gov + ArcGIS (~168 files; assessments, PEIMS finance) |
| `data/raw/federal/crdc/` | CRDC national zip bundles by school year |
| `data/raw/federal/crdc_extracted/` | Topic CSV/XLSX unpacked from CRDC zips |
| `data/raw/federal/edtech/` | NCES/ED technology & internet surveys |
| `data/raw/federal/spp/` | School Pulse Panel topic files |
| `data/raw/federal/{category}/` | Other federal files (discipline, enrollment, financials, …) |

### Cleaned (`data/cleaned/`) — state-filtered extracts from national files

State-only rows cut from NCES CCD (schools + F-33 district finance) and CRDC extracted CSVs.

| Path | Contents |
|------|----------|
| `data/cleaned/hawaii/` | HI-only NCES + CRDC (~50 files) |
| `data/cleaned/virginia/` | VA-only NCES + CRDC (~50 files) |
| `data/cleaned/colorado/` | CO-only NCES + CRDC + F-33 (~88 files) |
| `data/cleaned/texas/` | TX-only NCES + CRDC + F-33 (~87 files) |

**Raw vs cleaned:** These are different layers. Example: 32 Colorado raw files + 88 Colorado cleaned files = **120 datasets**, not 32 with 56 dropped.

---

## Project structure

```
notebooks/
  collect_education_data.ipynb         # HI/VA + baseline federal
  collect_federal_crdc_edtech.ipynb    # National CRDC + ed-tech + SPP (civil rights)
  collect_federal_broad_k12.ipynb      # Broader national K–12 (CCD, FRSS, SPP)
  collect_state_colorado_texas.ipynb   # Colorado + Texas state collection
scripts/
  federal_collect.py                   # Helpers for federal notebooks
  state_collect.py                     # Shared state download + Socrata helpers
  colorado_collect.py                  # Colorado seeds & API config
  texas_collect.py                     # Texas seeds, PEIMS cap, ArcGIS helpers
  broad_k12_collect.py                 # Helpers for broad K–12 notebook
  generate_docs.py                     # Build docs/SOURCES.md & SUPERVISOR_SUMMARY.md
  run_co_tx_collection.py              # CLI: Colorado + Texas collection
  build_co_tx_notebook.py              # Regenerate CO/TX notebook from script
  run_federal_expansion.py             # CLI: CRDC extract + FRSS expansion
  run_federal_wave2.py                 # CLI: SPP themes + optional CRDC zip
  build_federal_notebook.py            # Regenerate federal CRDC/ed-tech notebook
  build_broad_k12_notebook.py          # Regenerate broad K–12 notebook
data/raw/                              # Original downloads
data/cleaned/                          # State extracts from federal data
logs/
  manifest.csv                         # Master catalog (deduplicated by path)
  download_log.jsonl                   # Append-only audit log
  co_discovered_links.csv              # Colorado Socrata discovery catalog
  tx_discovered_links.csv              # Texas Socrata discovery catalog
  tx_arcgis_discovered.csv             # Texas ArcGIS inventory
docs/
  SOURCES.md                           # File-by-file source catalog
  SUPERVISOR_SUMMARY.md                # Non-technical overview
```

---

## What each notebook collects

### Notebook 1 — Hawaii, Virginia, and baseline federal

- Direct URL downloads (HIDOE, Virginia CKAN API)
- Web scraping (BeautifulSoup) for additional Hawaii links
- Federal NCES school directory + CRDC 2017–18
- HI/VA row extraction to `data/cleaned/`

### Notebook 2 — National CRDC and ed-tech

- CRDC public-use zips (2015–16, 2020–21) → `data/raw/federal/crdc/`
- Extract CRDC zips → `data/raw/federal/crdc_extracted/`
- NCES FRSS ed-tech surveys → `data/raw/federal/edtech/`
- School Pulse Panel (civil-rights topics)

### Notebook 3 — Broader national K–12

- NCES CCD school universe, state nonfiscal, district finance (F-33)
- FRSS facilities, dual credit, English learners
- School Pulse Panel staffing, facilities, college readiness

**Prerequisite:** Notebook 2 (CRDC zips on disk and extracted).

### Notebook 4 — Colorado & Texas (max mode)

- **Phase 1:** Direct CDE/TEA URLs
- **Phase 2–3:** Socrata API (exportable tabular datasets only; rate-limit retries)
- **Phase 4–5:** BeautifulSoup harvest of CDE and TEA pages
- **Phase 6a–6b:** Texas ArcGIS catalog + CSV/ZIP downloads
- **Phase 7:** Filter NCES schools + F-33 district finance + CRDC → `data/cleaned/{state}/`
- **Phase 8:** Manifest refresh and summary

Tune in Step 0.2: `MAX_TX_PEIMS_ZIP_DOWNLOADS = 0` (all PEIMS years) or `6` (newest six only).

---

## Reproducibility

- Re-runs **skip files already on disk** where configured (`skipped_exists` in the log).
- Every action is appended to `logs/download_log.jsonl`.
- Re-run `py -3 scripts/generate_docs.py` after new downloads to refresh `docs/`.

---

## GitHub / large files

GitHub rejects files **> 100 MB**. The following are listed in `.gitignore` and can be re-downloaded via the notebooks:

- `data/raw/federal/crdc_extracted/2015-16/…School Data.csv` (~443 MB)
- `data/raw/colorado/discipline/socrata_6vnq-az4b.csv` (~594 MB; Colorado crimes open data)
- Several large federal zips in `data/raw/federal/other/` and `data/raw/federal/crdc/`

If push fails on a new large file, add its path to `.gitignore` and document the re-download step here.

---

## Requirements

See [`requirements.txt`](requirements.txt): `requests`, `beautifulsoup4`, `pandas`, `openpyxl`, `pdfplumber`, `jupyter`.
