"""Generate docs/SOURCES.md and docs/SUPERVISOR_SUMMARY.md from manifest + cleaned files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT / "logs/manifest.csv"
SOURCES_OUT = PROJECT / "docs/SOURCES.md"
SUMMARY_OUT = PROJECT / "docs/SUPERVISOR_SUMMARY.md"
CATEGORIES = ["test_scores", "enrollment", "financials", "teachers", "discipline", "other"]


def norm_path(p: str) -> str:
    return str(p).replace("\\", "/")


def category_file_counts(root: Path) -> dict[str, int]:
    counts = {cat: 0 for cat in CATEGORIES}
    if not root.exists():
        return counts
    for path in root.rglob("*"):
        if path.is_file():
            cat = path.parent.name
            counts[cat] = counts.get(cat, 0) + 1
    return counts


def build_combined_summary(raw_root: Path, cleaned_root: Path) -> pd.DataFrame:
    raw_counts = category_file_counts(raw_root)
    clean_counts = category_file_counts(cleaned_root)
    rows = []
    for cat in CATEGORIES:
        r = raw_counts.get(cat, 0)
        c = clean_counts.get(cat, 0)
        rows.append(
            {
                "category": cat,
                "raw_state_downloads": r,
                "cleaned_federal_extracts": c,
                "total_datasets": r + c,
            }
        )
    df = pd.DataFrame(rows)
    totals = pd.DataFrame(
        [
            {
                "category": "TOTAL",
                "raw_state_downloads": df["raw_state_downloads"].sum(),
                "cleaned_federal_extracts": df["cleaned_federal_extracts"].sum(),
                "total_datasets": df["total_datasets"].sum(),
            }
        ]
    )
    return pd.concat([df, totals], ignore_index=True)


def md_table(df: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            val = row[col]
            if pd.isna(val):
                val = ""
            val = str(val).replace("|", "\\|").replace("\n", " ")
            cells.append(val)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load_cleaned_inventory() -> pd.DataFrame:
    cleaned_rows = []
    for state in ["hawaii", "virginia"]:
        root = PROJECT / "data/cleaned" / state
        abbr = "HI" if state == "hawaii" else "VA"
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            name = p.name
            cat = p.parent.name
            rel = norm_path(p.relative_to(PROJECT))
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
            if name.startswith("nces_"):
                desc = f"NCES public school directory ({abbr} rows only, 2018-19)"
                url = "https://nces.ed.gov/ccd/files.asp"
            elif name.startswith("crdc_"):
                topic = name.replace("crdc_", "").replace(f"_{abbr}.csv", "").replace(
                    "_", " "
                )
                desc = f"CRDC 2017-18: {topic} ({abbr} rows only)"
                url = "https://ocrdata.ed.gov/estimations/2017-18"
            else:
                desc = f"State-filtered extract ({abbr})"
                url = ""
            cleaned_rows.append(
                {
                    "state": state,
                    "category": cat,
                    "description": desc,
                    "url": url,
                    "local_path": rel,
                    "date_downloaded": mtime,
                }
            )
    return pd.DataFrame(cleaned_rows)


def main() -> None:
    m = pd.read_csv(MANIFEST)
    m = m.sort_values("timestamp_utc").drop_duplicates(subset=["local_path"], keep="last")
    m["local_path"] = m["local_path"].map(norm_path)
    m["date_downloaded"] = pd.to_datetime(m["timestamp_utc"], utc=True).dt.strftime(
        "%Y-%m-%d"
    )

    cleaned_df = load_cleaned_inventory()

    hi_table = build_combined_summary(
        PROJECT / "data/raw/hawaii", PROJECT / "data/cleaned/hawaii"
    )
    va_table = build_combined_summary(
        PROJECT / "data/raw/virginia", PROJECT / "data/cleaned/virginia"
    )
    hi_table.insert(0, "state", "Hawaii")
    va_table.insert(0, "state", "Virginia")
    combined = pd.concat([hi_table, va_table], ignore_index=True)

    lines: list[str] = []
    lines.append("# Data sources catalog (Hawaii & Virginia)\n")
    lines.append(
        "Generated from `logs/manifest.csv` (deduplicated by file path) plus "
        "`data/cleaned/` extracts.\n"
    )
    lines.append(
        "Regenerate after new downloads: `python scripts/generate_docs.py`\n"
    )

    lines.append("## Collection overview\n")
    lines.append("| Item | Location | Count |")
    lines.append("| --- | --- | ---: |")
    lines.append(
        f"| Hawaii state downloads | `data/raw/hawaii/` | {len(m[m.state == 'hawaii'])} |"
    )
    lines.append(
        f"| Virginia state downloads | `data/raw/virginia/` | {len(m[m.state == 'virginia'])} |"
    )
    lines.append(
        f"| Federal national downloads | `data/raw/federal/` | {len(m[m.state == 'federal'])} |"
    )
    lines.append(
        f"| Hawaii cleaned extracts | `data/cleaned/hawaii/` | {len(cleaned_df[cleaned_df.state == 'hawaii'])} |"
    )
    lines.append(
        f"| Virginia cleaned extracts | `data/cleaned/virginia/` | {len(cleaned_df[cleaned_df.state == 'virginia'])} |"
    )
    lines.append(
        f"| **Total cataloged files** | | **{len(m) + len(cleaned_df)}** |\n"
    )

    lines.append("## Primary portals used\n")
    lines.append("| Portal | Used for |")
    lines.append("| --- | --- |")
    lines.append(
        "| [Hawaii DOE / hawaiipublicschools.org](https://hawaiipublicschools.org/) | Hawaii enrollment, reports, PDF catalog |"
    )
    lines.append(
        "| [hcnp.hawaii.gov/fiscal](https://hcnp.hawaii.gov/fiscal/) | Hawaii child nutrition / fiscal reports |"
    )
    lines.append(
        "| [Virginia Open Data (data.virginia.gov)](https://data.virginia.gov/) | Bulk Virginia VDOE datasets (CKAN API) |"
    )
    lines.append(
        "| [NCES CCD](https://nces.ed.gov/ccd/) | National school directory (filtered to HI/VA) |"
    )
    lines.append(
        "| [CRDC / data.ed.gov](https://data.ed.gov/) | Civil Rights Data Collection 2017-18 (filtered to HI/VA) |\n"
    )

    lines.append("## Raw vs cleaned\n")
    lines.append(
        "- **`data/raw/`** — original files downloaded from state or federal websites."
    )
    lines.append(
        "- **`data/cleaned/`** — Hawaii- or Virginia-only rows extracted from federal "
        "NCES and CRDC national files (not copies of the raw state downloads).\n"
    )

    lines.append("## Files by category (summary)\n")
    lines.append(
        md_table(
            combined,
            [
                "state",
                "category",
                "raw_state_downloads",
                "cleaned_federal_extracts",
                "total_datasets",
            ],
        )
    )
    lines.append("")

    catalog_cols = [
        "state",
        "category",
        "description",
        "url",
        "local_path",
        "date_downloaded",
    ]

    def append_catalog_section(title: str, df: pd.DataFrame) -> None:
        lines.append(f"## {title}\n")
        if df.empty:
            lines.append("_No files._\n")
            return
        out = df[catalog_cols].copy()
        lines.append(md_table(out, catalog_cols))
        lines.append("")

    for state_key, title in [
        ("hawaii", "Hawaii — state downloads (`data/raw/hawaii/`)"),
        ("virginia", "Virginia — state downloads (`data/raw/virginia/`)"),
        ("federal", "Federal — national downloads (`data/raw/federal/`)"),
    ]:
        sub = m[m.state == state_key].sort_values(["category", "local_path"])
        append_catalog_section(title, sub)

    for state_key, title in [
        ("hawaii", "Hawaii — cleaned extracts (`data/cleaned/hawaii/`)"),
        ("virginia", "Virginia — cleaned extracts (`data/cleaned/virginia/`)"),
    ]:
        sub = cleaned_df[cleaned_df.state == state_key].sort_values(
            ["category", "local_path"]
        )
        append_catalog_section(title, sub)

    lines.append("---\n")
    lines.append(
        f"_Catalog generated {datetime.now().strftime('%Y-%m-%d')}. "
        "Machine-readable log: `logs/manifest.csv`._\n"
    )

    SOURCES_OUT.write_text("\n".join(lines), encoding="utf-8")

    hi_total_raw = int(
        hi_table.loc[hi_table.category == "TOTAL", "raw_state_downloads"].iloc[0]
    )
    hi_total_clean = int(
        hi_table.loc[hi_table.category == "TOTAL", "cleaned_federal_extracts"].iloc[0]
    )
    va_total_raw = int(
        va_table.loc[va_table.category == "TOTAL", "raw_state_downloads"].iloc[0]
    )
    va_total_clean = int(
        va_table.loc[va_table.category == "TOTAL", "cleaned_federal_extracts"].iloc[0]
    )

    summary = f"""# EOQ Lab — Data Collection Summary (Hawaii & Virginia)

**Prepared for:** Supervisor review  
**Date:** {datetime.now().strftime("%B %d, %Y")}

## What was delivered

This project collected publicly available U.S. public education data for **Hawaii** and **Virginia** using a reproducible Python workflow in `notebooks/collect_education_data.ipynb`. All downloads are logged in `logs/manifest.csv`.

| Deliverable | Location |
| --- | --- |
| Collection notebook | `notebooks/collect_education_data.ipynb` |
| Original downloads | `data/raw/` |
| State-filtered federal extracts | `data/cleaned/` |
| Download log & manifest | `logs/manifest.csv`, `logs/download_log.jsonl` |
| Full source catalog | `docs/SOURCES.md` |

## How the data is organized

We used two complementary layers:

1. **Raw state downloads** (`data/raw/hawaii/`, `data/raw/virginia/`) — files pulled directly from Hawaii DOE, Hawaii child-nutrition fiscal pages, and Virginia's Open Data portal.
2. **Cleaned state extracts** (`data/cleaned/hawaii/`, `data/cleaned/virginia/`) — Hawaii-only or Virginia-only rows cut from **national** NCES school directory and CRDC 2017-18 files. These are *additional* datasets, not filtered-down versions of the raw state files.

**Important:** If Hawaii raw shows 78 files and cleaned shows 50, that does **not** mean 28 files were dropped. All 78 raw files remain in place; the 50 cleaned files come from separate federal sources.

## Files by category

{md_table(combined, ["state", "category", "raw_state_downloads", "cleaned_federal_extracts", "total_datasets"])}

### Totals

| State | Raw (state downloads) | Cleaned (federal extracts) | Combined datasets |
| --- | ---: | ---: | ---: |
| Hawaii | {hi_total_raw} | {hi_total_clean} | {hi_total_raw + hi_total_clean} |
| Virginia | {va_total_raw} | {va_total_clean} | {va_total_raw + va_total_clean} |
| **Both states** | **{hi_total_raw + va_total_raw}** | **{hi_total_clean + va_total_clean}** | **{hi_total_raw + hi_total_clean + va_total_raw + va_total_clean}** |

Plus **{len(m[m.state == 'federal'])}** federal national files in `data/raw/federal/` (source zips for NCES/CRDC and other U.S.-wide datasets).

## Collection methods (brief)

| Method | What it collected |
| --- | --- |
| Direct URL download | Known Hawaii DOE file links |
| Virginia CKAN API | ~220 VDOE datasets from data.virginia.gov |
| Web page link scraping | Additional Hawaii HIDOE and hcnf.hawaii.gov links |
| PDF catalog parsing | Hawaii publicly available reports list |
| Federal API / catalog | NCES and CRDC national files |
| Phase 6 processing | Improved file categorization; HI/VA row extraction from federal zips |

## Known limitations

- **Hawaii state test scores:** No automated exports from HIDOE dashboard sites (ARCH/Strive HI); test-score coverage comes mainly from CRDC cleaned files.
- **Teachers category:** Limited direct state downloads; some teacher-related CRDC topics are filed under `other/`.
- **Virginia:** Some doe.virginia.gov HTML pages returned HTTP 403; bulk coverage comes from the Open Data API.

## How to reproduce

1. Install dependencies: `pip install -r requirements.txt`
2. Open and run `notebooks/collect_education_data.ipynb` top to bottom.
3. See `README.md` for folder layout.

---

_For the complete file-by-file list with URLs and download dates, see `docs/SOURCES.md`._
"""

    SUMMARY_OUT.write_text(summary, encoding="utf-8")

    print(f"Wrote {SOURCES_OUT} ({len(lines)} lines)")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Catalog entries: manifest={len(m)}, cleaned={len(cleaned_df)}")


if __name__ == "__main__":
    main()
