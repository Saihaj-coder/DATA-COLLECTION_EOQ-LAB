# EOQ Lab — Data Collection Summary

**Prepared for:** Supervisor review  
**Date:** July 01, 2026

## What was delivered

Public U.S. K–12 education data for **four states** (Hawaii, Virginia, Colorado, Texas) plus **national federal** sources, collected via reproducible Jupyter notebooks. All downloads are logged in `logs/manifest.csv`.

| Deliverable | Location |
| --- | --- |
| Hawaii & Virginia notebook | `notebooks/collect_education_data.ipynb` |
| National CRDC & ed-tech notebook | `notebooks/collect_federal_crdc_edtech.ipynb` |
| Broad national K–12 notebook | `notebooks/collect_federal_broad_k12.ipynb` |
| Colorado & Texas notebook | `notebooks/collect_state_colorado_texas.ipynb` |
| Original downloads | `data/raw/` |
| State-filtered federal extracts | `data/cleaned/` |
| Download log & manifest | `logs/manifest.csv`, `logs/download_log.jsonl` |
| Full source catalog | `docs/SOURCES.md` |

## How the data is organized

1. **Raw state downloads** (`data/raw/{state}/`) — files from state DOE portals, open-data APIs, and web scraping.
2. **Cleaned state extracts** (`data/cleaned/{state}/`) — state-only rows from national NCES (schools, F-33 finance) and CRDC topic files.

Raw and cleaned counts are **additive**, not overlapping.

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
| Colorado | test_scores | 20 | 16 | 36 |
| Colorado | enrollment | 4 | 20 | 24 |
| Colorado | financials | 0 | 4 | 4 |
| Colorado | teachers | 0 | 0 | 0 |
| Colorado | discipline | 1 | 10 | 11 |
| Colorado | other | 7 | 38 | 45 |
| Colorado | TOTAL | 32 | 88 | 120 |
| Texas | test_scores | 124 | 16 | 140 |
| Texas | enrollment | 1 | 19 | 20 |
| Texas | financials | 33 | 4 | 37 |
| Texas | teachers | 1 | 0 | 1 |
| Texas | discipline | 0 | 10 | 10 |
| Texas | other | 9 | 38 | 47 |
| Texas | TOTAL | 168 | 87 | 255 |

### Totals

| State | Raw (state downloads) | Cleaned (federal extracts) | Combined datasets |
| --- | ---: | ---: | ---: |
| Hawaii | 78 | 50 | 128 |
| Virginia | 220 | 50 | 270 |
| Colorado | 32 | 88 | 120 |
| Texas | 168 | 87 | 255 |
| **All four states** | **498** | **275** | **773** |

Plus **482** federal files on disk under `data/raw/federal/` (2 CRDC zips, 55 ed-tech survey files).

## Collection methods

| Method | States / scope |
| --- | --- |
| Direct URL download | HI, CO, TX hand-picked files |
| Virginia CKAN API | VA (~220 datasets) |
| Socrata open data API | CO, TX (exportable CSV datasets) |
| BeautifulSoup HTML harvest | HI, CO (CDE), TX (TEA) |
| ArcGIS Online `/data` URLs | TX geography & CTE layers |
| NCES + CRDC federal filter | HI, VA, CO, TX → `data/cleaned/` |

## Known limitations

- **Hawaii test scores:** Limited HIDOE exports; CRDC cleaned files fill gaps.
- **Colorado:** Thin state financials/teachers; one large Socrata crime dataset (~594 MB) is gitignored (re-download via notebook).
- **Texas:** Strong PEIMS/assessments; discipline data not yet harvested from TEA pages.
- **Federal:** Some data.ed.gov URLs time out; CRDC zips are the primary national source.
- **Vintage:** NCES school universe is 2018-19; F-33 district finance is 2018.

## How to reproduce

See `README.md`. Install `requirements.txt`, run notebooks in order, then `python scripts/generate_docs.py`.

---

_For the complete file-by-file list with URLs and download dates, see `docs/SOURCES.md`._
