# EOQ Lab — Public Education Data Collection (Hawaii & Virginia)

Collects publicly available education data files for **Hawaii** and **Virginia** using a Jupyter notebook workflow.

## Quick start

1. Open `notebooks/collect_education_data.ipynb` in Jupyter or Cursor.
2. Run cells **top to bottom** (Kernel → Restart & Run All after changes).
3. Downloaded files appear under `data/raw/`.
4. Logs and manifests appear under `logs/`.

## Install packages (optional, outside notebook)

```bash
pip install -r requirements.txt
```

## Project layout

- `notebooks/` — main collection notebook (step-by-step)
- `data/raw/` — original downloaded files (do not edit)
- `data/cleaned/` — optional cleaned copies
- `logs/` — download logs and link discovery tables
- `docs/SOURCES.md` — full file-by-file catalog (URLs, paths, dates)
- `docs/SUPERVISOR_SUMMARY.md` — short overview for non-technical readers

## Reproducibility

Re-run the notebook to refresh downloads. Raw files are never overwritten in place without logging; see notebook settings.

## GitHub note

Six federal ZIP files exceed GitHub's 100 MB file limit and are listed in `.gitignore`. They remain on your local machine under `data/raw/federal/`. Re-run **Phase 4** in the notebook on a fresh clone to download them again. All other data, logs, docs, and the notebook are included in this repo.

Regenerate documentation after new downloads:

```bash
python scripts/generate_docs.py
```
