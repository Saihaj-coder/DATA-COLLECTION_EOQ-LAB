# EOQ Lab — Public Education Data Collection

Reproducible Python/Jupyter workflow for collecting publicly available U.S. public education data.

**Coverage:**
- **Hawaii & Virginia** — state downloads (DOE, Open Data API, web scraping)
- **National federal** — Civil Rights Data Collection (CRDC), NCES, and ed-tech surveys (all U.S. states)

All downloads are logged to `logs/manifest.csv`.

---

## Notebooks

Run in Cursor or Jupyter. Install dependencies once (see below), then run each notebook **top to bottom**.

| Notebook | Purpose | Prerequisite |
|----------|---------|--------------|
| [`notebooks/collect_education_data.ipynb`](notebooks/collect_education_data.ipynb) | Hawaii + Virginia state data; federal NCES/CRDC; HI/VA cleaned extracts | None |
| [`notebooks/collect_federal_crdc_edtech.ipynb`](notebooks/collect_federal_crdc_edtech.ipynb) | National CRDC (2015–16, 2020–21) + technology-in-schools surveys | Notebook 1 recommended (shared logs & folders) |
| [`notebooks/collect_federal_broad_k12.ipynb`](notebooks/collect_federal_broad_k12.ipynb) | Broader national K–12: enrollment, finance, staffing, facilities (NCES CCD, SPP, FRSS) | `collect_federal_crdc_edtech.ipynb` (CRDC zips extracted) |

**Tip:** Skip `%pip install` cells if packages are already installed. After code changes in `scripts/`, restart the kernel before re-running.

---

## Quick start

```bash
pip install -r requirements.txt
```

1. Open `notebooks/collect_education_data.ipynb` → Run All (first-time full collection).
2. Open `notebooks/collect_federal_crdc_edtech.ipynb` → Run All (national CRDC + ed-tech + extract).
3. Open `notebooks/collect_federal_broad_k12.ipynb` → Run All (broader national K–12).
4. Check outputs under `data/raw/` and summary in `logs/manifest.csv`.

Regenerate documentation catalogs:

```bash
python scripts/generate_docs.py
```

---

## Data layout

### Raw (`data/raw/`) — original downloads; do not edit by hand

| Path | Contents |
|------|----------|
| `data/raw/hawaii/` | Hawaii DOE, HIDOE, hcnf fiscal reports (~78 files) |
| `data/raw/virginia/` | Virginia Open Data (VDOE) datasets (~220 files) |
| `data/raw/federal/crdc/` | CRDC national zip bundles by school year |
| `data/raw/federal/crdc_extracted/` | Topic CSV/XLSX unpacked from CRDC zips (ready for analysis) |
| `data/raw/federal/edtech/` | NCES/ED technology & internet access surveys |
| `data/raw/federal/spp/` | School Pulse Panel (SPP) topic files |
| `data/raw/federal/{category}/` | Other federal files (discipline, enrollment, financials, test scores, teachers, …) |

### Cleaned (`data/cleaned/`) — state-filtered extracts from national files

Hawaii- or Virginia-only rows cut from federal NCES + CRDC zips (not copies of raw state downloads).

| Path | Contents |
|------|----------|
| `data/cleaned/hawaii/` | HI-only NCES + CRDC CSVs (~50 files) |
| `data/cleaned/virginia/` | VA-only NCES + CRDC CSVs (~50 files) |

**Raw vs cleaned:** These are different layers. Example: 78 Hawaii raw files + 50 Hawaii cleaned files = **128 datasets**, not 78 with 28 dropped.

---

## Project structure

```
notebooks/
  collect_education_data.ipynb         # HI/VA + baseline federal
  collect_federal_crdc_edtech.ipynb    # National CRDC + ed-tech + SPP (civil rights)
  collect_federal_broad_k12.ipynb      # Broader national K–12 (CCD, FRSS, SPP)
scripts/
  federal_collect.py                   # Helpers for federal notebooks
  broad_k12_collect.py                 # Helpers for broad K–12 notebook
  generate_docs.py                     # Build docs/SOURCES.md & SUPERVISOR_SUMMARY.md
  run_federal_expansion.py             # CLI: CRDC extract + FRSS expansion
  run_federal_wave2.py                 # CLI: SPP themes + optional 2021–22 CRDC zip
  build_federal_notebook.py            # Regenerate federal CRDC/ed-tech notebook
  build_broad_k12_notebook.py          # Regenerate broad K–12 notebook
data/raw/                              # Original downloads
data/cleaned/                          # HI/VA extracts from federal data
logs/
  manifest.csv                         # Master catalog (all downloads)
  download_log.jsonl                   # Append-only audit log
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
- Improved file categorization; HI/VA row extraction to `data/cleaned/`

### Notebook 2 — National CRDC and ed-tech

- **Phase 1:** CRDC public-use zips (2015–16, 2020–21) → `data/raw/federal/crdc/`
- **Phase 2:** Inventory topics inside zips (incl. Internet Access and Devices in 2020–21)
- **Phase 3:** Individual CRDC spreadsheets from data.ed.gov (optional; many URLs may fail)
- **Phase 4:** NCES FRSS ed-tech / internet surveys → `data/raw/federal/edtech/`
- **Phase 5:** Refresh `logs/manifest.csv` and print summary
- **Phase 6:** Extract CRDC zips → `data/raw/federal/crdc_extracted/`; download extended FRSS surveys
- **Phase 7:** School Pulse Panel (civil rights + ed-tech topics) via `scripts/run_federal_wave2.py`

Some individual URLs may fail (502/504 from data.ed.gov); the notebook logs them and continues. The CRDC zip files and local extracts are the primary national deliverables.

### Notebook 3 — Broader national K–12

- **Phase 1:** Catalog CRDC extracts (enrollment, AP, graduation, …)
- **Phase 2:** Re-extract CRDC zips if new years were added
- **Phase 3:** NCES CCD — school universe, state nonfiscal, district finance (F-33)
- **Phase 4:** FRSS — facilities, dual credit, English learners
- **Phase 5:** School Pulse Panel — staffing, facilities, college readiness → `data/raw/federal/spp/broad_k12/`
- **Phase 6:** Refresh manifest and print summary

**Prerequisite:** Run Notebook 2 first so CRDC zips are on disk and extracted.

---

## Reproducibility

- Downloads use `skip_if_exists` where configured — re-runs skip files already on disk.
- Every download is appended to `logs/download_log.jsonl`.
- Re-run `python scripts/generate_docs.py` after new downloads to refresh `docs/`.

---

## Requirements

See [`requirements.txt`](requirements.txt): `requests`, `beautifulsoup4`, `pandas`, `openpyxl`, `pdfplumber`, `jupyter`.
