# EOQ Lab — Data Collection Summary

**Prepared for:** Supervisor review  
**Date:** June 12, 2026

## What was delivered

This project collected publicly available U.S. public education data in two phases using reproducible Jupyter notebooks. All downloads are logged in `logs/manifest.csv`.

| Deliverable | Location |
| --- | --- |
| Hawaii & Virginia notebook | `notebooks/collect_education_data.ipynb` |
| National CRDC & ed-tech notebook | `notebooks/collect_federal_crdc_edtech.ipynb` |
| Original downloads | `data/raw/` |
| State-filtered federal extracts | `data/cleaned/` |
| Download log & manifest | `logs/manifest.csv`, `logs/download_log.jsonl` |
| Full source catalog | `docs/SOURCES.md` |

### Phase 1 — Hawaii & Virginia

State downloads from Hawaii DOE, Hawaii child-nutrition fiscal pages, and Virginia Open Data; baseline federal NCES/CRDC; HI/VA row extracts in `data/cleaned/`.

### Phase 2 — National federal (CRDC & ed-tech)

CRDC public-use zips (2015-16, 2020-21), individual CRDC spreadsheets from data.ed.gov, and NCES FRSS technology/internet surveys — all U.S. states, stored under `data/raw/federal/crdc/` and `data/raw/federal/edtech/`.

## How the data is organized

We used two complementary layers:

1. **Raw state downloads** (`data/raw/hawaii/`, `data/raw/virginia/`) — files pulled directly from Hawaii DOE, Hawaii child-nutrition fiscal pages, and Virginia's Open Data portal.
2. **Cleaned state extracts** (`data/cleaned/hawaii/`, `data/cleaned/virginia/`) — Hawaii-only or Virginia-only rows cut from **national** NCES school directory and CRDC 2017-18 files. These are *additional* datasets, not filtered-down versions of the raw state files.

**Important:** If Hawaii raw shows 78 files and cleaned shows 50, that does **not** mean 28 files were dropped. All 78 raw files remain in place; the 50 cleaned files come from separate federal sources.

## Files by category

| state | category | raw_state_downloads | cleaned_federal_extracts | total_datasets |
| --- | --- | --- | --- | --- |
| Hawaii | test_scores | 0 | 6 | 6 |
| Hawaii | enrollment | 40 | 3 | 43 |
| Hawaii | financials | 18 | 1 | 19 |
| Hawaii | teachers | 0 | 0 | 0 |
| Hawaii | discipline | 0 | 5 | 5 |
| Hawaii | other | 20 | 35 | 55 |
| Hawaii | TOTAL | 78 | 50 | 128 |
| Virginia | test_scores | 24 | 6 | 30 |
| Virginia | enrollment | 79 | 3 | 82 |
| Virginia | financials | 4 | 1 | 5 |
| Virginia | teachers | 0 | 0 | 0 |
| Virginia | discipline | 6 | 5 | 11 |
| Virginia | other | 107 | 35 | 142 |
| Virginia | TOTAL | 220 | 50 | 270 |

### Totals

| State | Raw (state downloads) | Cleaned (federal extracts) | Combined datasets |
| --- | ---: | ---: | ---: |
| Hawaii | 78 | 50 | 128 |
| Virginia | 220 | 50 | 270 |
| **Both states** | **298** | **100** | **398** |

Plus **351** federal national files in `data/raw/federal/` — including **2** CRDC zip bundles and **46** ed-tech survey files.

## Collection methods (brief)

| Method | What it collected |
| --- | --- |
| Direct URL download | Known Hawaii DOE file links |
| Virginia CKAN API | ~220 VDOE datasets from data.virginia.gov |
| Web page link scraping | Additional Hawaii HIDOE and hcnf.hawaii.gov links |
| PDF catalog parsing | Hawaii publicly available reports list |
| Federal API / catalog | NCES and CRDC national files |
| Phase 6 processing | Improved file categorization; HI/VA row extraction from federal zips |
| CRDC zip + API downloads | National civil-rights datasets (2015-16, 2020-21) |
| NCES FRSS ed-tech surveys | Internet access, devices, computer science in schools |

## Known limitations

- **Hawaii state test scores:** No automated exports from HIDOE dashboard sites (ARCH/Strive HI); test-score coverage comes mainly from CRDC cleaned files.
- **Teachers category:** Limited direct state downloads; some teacher-related CRDC topics are filed under `other/`.
- **Virginia:** Some doe.virginia.gov HTML pages returned HTTP 403; bulk coverage comes from the Open Data API.
- **Federal Phase 3:** Some individual CRDC spreadsheet URLs on data.ed.gov timed out (502/504); the CRDC zip files remain the primary national deliverables.

## How to reproduce

1. Install dependencies: `pip install -r requirements.txt`
2. Run `notebooks/collect_education_data.ipynb` top to bottom.
3. Run `notebooks/collect_federal_crdc_edtech.ipynb` top to bottom.
4. Regenerate docs: `python scripts/generate_docs.py`
5. See `README.md` for folder layout.

---

_For the complete file-by-file list with URLs and download dates, see `docs/SOURCES.md`._
