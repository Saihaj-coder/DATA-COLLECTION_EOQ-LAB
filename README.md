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

**Tip:** Skip `%pip install` cells if packages are already installed. After code changes in `scripts/`, restart the kernel before re-running.

---

## Quick start

```bash
pip install -r requirements.txt
```

1. Open `notebooks/collect_education_data.ipynb` → Run All (first-time full collection).
2. Open `notebooks/collect_federal_crdc_edtech.ipynb` → Run All (adds national CRDC + ed-tech).
3. Check outputs under `data/raw/` and summary in `logs/manifest.csv`.

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
| `data/raw/federal/edtech/` | NCES/ED technology & internet access surveys |
| `data/raw/federal/{category}/` | Other federal files (discipline, enrollment, test scores, …) |

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
  collect_education_data.ipynb      # HI/VA + federal Phase 4–6
  collect_federal_crdc_edtech.ipynb # National CRDC + ed-tech
scripts/
  federal_collect.py                # Helpers for federal notebook
  generate_docs.py                  # Build docs/SOURCES.md & SUPERVISOR_SUMMARY.md
data/raw/                           # Original downloads
data/cleaned/                       # HI/VA extracts from federal data
logs/
  manifest.csv                      # Master catalog (all downloads)
  download_log.jsonl                # Append-only audit log
docs/
  SOURCES.md                        # File-by-file source catalog
  SUPERVISOR_SUMMARY.md             # Non-technical overview
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
- **Phase 3:** Individual CRDC spreadsheets from data.ed.gov (2015–16, 2020–21)
- **Phase 4:** NCES FRSS ed-tech / internet surveys → `data/raw/federal/edtech/`
- **Phase 5:** Refresh `logs/manifest.csv` and print summary

Some individual URLs may fail (502/504 from data.ed.gov); the notebook logs them and continues. The CRDC zip files are the primary national deliverables.

---

## Reproducibility

- Downloads use `skip_if_exists` where configured — re-runs skip files already on disk.
- Every download is appended to `logs/download_log.jsonl`.
- Re-run `python scripts/generate_docs.py` after new downloads to refresh `docs/`.

---

## Requirements

See [`requirements.txt`](requirements.txt): `requests`, `beautifulsoup4`, `pandas`, `openpyxl`, `pdfplumber`, `jupyter`.
