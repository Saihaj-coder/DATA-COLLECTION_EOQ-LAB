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

# slug, display name, postal abbreviation
STATES = [
    ("hawaii", "Hawaii", "HI"),
    ("virginia", "Virginia", "VA"),
    ("colorado", "Colorado", "CO"),
    ("texas", "Texas", "TX"),
]


def norm_path(p: str) -> str:
    return str(p).replace("\\", "/")


def count_files_under(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


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


def cleaned_file_description(name: str, abbr: str) -> tuple[str, str]:
    if name.startswith("nces_public_schools_"):
        return (
            f"NCES CCD public school universe ({abbr} rows only, 2018-19)",
            "https://nces.ed.gov/ccd/pubschuniv.asp",
        )
    if name.startswith("nces_district_finance_"):
        return (
            f"NCES CCD district finance F-33 ({abbr} rows only, 2018)",
            "https://nces.ed.gov/ccd/f33agency.asp",
        )
    if name.startswith("crdc_"):
        topic = name.replace("crdc_", "").replace(f"_{abbr}.csv", "").replace("_", " ")
        return (
            f"CRDC extract: {topic} ({abbr} rows only)",
            "https://civilrightsdata.ed.gov/",
        )
    return (f"State-filtered extract ({abbr})", "")


def load_cleaned_inventory() -> pd.DataFrame:
    cleaned_rows = []
    for slug, _, abbr in STATES:
        root = PROJECT / "data/cleaned" / slug
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            desc, url = cleaned_file_description(p.name, abbr)
            cleaned_rows.append(
                {
                    "state": slug,
                    "category": p.parent.name,
                    "description": desc,
                    "url": url,
                    "local_path": norm_path(p.relative_to(PROJECT)),
                    "date_downloaded": datetime.fromtimestamp(
                        p.stat().st_mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%d"),
                }
            )
    return pd.DataFrame(cleaned_rows)


def state_totals(table: pd.DataFrame) -> tuple[int, int]:
    row = table.loc[table.category == "TOTAL"].iloc[0]
    return int(row.raw_state_downloads), int(row.cleaned_federal_extracts)


def main() -> None:
    m = pd.read_csv(MANIFEST)
    m = m.sort_values("timestamp_utc").drop_duplicates(subset=["local_path"], keep="last")
    m["local_path"] = m["local_path"].map(norm_path)
    m["date_downloaded"] = pd.to_datetime(m["timestamp_utc"], utc=True).dt.strftime(
        "%Y-%m-%d"
    )

    cleaned_df = load_cleaned_inventory()

    state_tables: list[pd.DataFrame] = []
    totals_by_state: dict[str, tuple[int, int]] = {}
    for slug, label, _ in STATES:
        table = build_combined_summary(
            PROJECT / "data/raw" / slug, PROJECT / "data/cleaned" / slug
        )
        table.insert(0, "state", label)
        state_tables.append(table)
        totals_by_state[slug] = state_totals(table)
    combined = pd.concat(state_tables, ignore_index=True)

    fed_crdc = count_files_under(PROJECT / "data/raw/federal/crdc")
    fed_edtech = count_files_under(PROJECT / "data/raw/federal/edtech")
    fed_files_on_disk = count_files_under(PROJECT / "data/raw/federal")
    fed_total_manifest = len(m[m.state == "federal"])

    lines: list[str] = []
    lines.append("# Data sources catalog (Hawaii, Virginia, Colorado, Texas & Federal)\n")
    lines.append(
        "Generated from `logs/manifest.csv` (deduplicated by file path) plus "
        "`data/cleaned/` extracts.\n"
    )
    lines.append("Regenerate after new downloads: `python scripts/generate_docs.py`\n")

    lines.append("## Collection overview\n")
    lines.append("| Item | Location | Count |")
    lines.append("| --- | --- | ---: |")
    for slug, label, _ in STATES:
        raw_n = count_files_under(PROJECT / "data/raw" / slug)
        clean_n = len(cleaned_df[cleaned_df.state == slug])
        lines.append(f"| {label} state downloads | `data/raw/{slug}/` | {raw_n} |")
        lines.append(f"| {label} cleaned extracts | `data/cleaned/{slug}/` | {clean_n} |")
    lines.append(f"| Federal national downloads (manifest) | `data/raw/federal/` | {fed_total_manifest} |")
    lines.append(f"| — CRDC public-use zips | `data/raw/federal/crdc/` | {fed_crdc} |")
    lines.append(f"| — Ed-tech / internet surveys | `data/raw/federal/edtech/` | {fed_edtech} |")
    lines.append(f"| Federal files on disk | `data/raw/federal/` | {fed_files_on_disk} |")
    lines.append(f"| **Total cataloged entries** | | **{len(m) + len(cleaned_df)}** |\n")

    lines.append("## Primary portals used\n")
    lines.append("| Portal | Used for |")
    lines.append("| --- | --- |")
    lines.append("| [Hawaii DOE](https://hawaiipublicschools.org/) | Hawaii enrollment, reports |")
    lines.append("| [Virginia Open Data](https://data.virginia.gov/) | VDOE datasets (CKAN API) |")
    lines.append("| [Colorado Open Data](https://data.colorado.gov/) | CDE datasets (Socrata API) |")
    lines.append("| [CDE](https://www.cde.state.co.us/) | Colorado accountability & assessment files |")
    lines.append("| [Texas Open Data](https://data.texas.gov/) | TEA datasets (Socrata API) |")
    lines.append("| [TEA](https://tea.texas.gov/) | PEIMS, STAAR, ArcGIS open data |")
    lines.append("| [NCES CCD](https://nces.ed.gov/ccd/) | School universe & district finance (filtered per state) |")
    lines.append("| [CRDC](https://civilrightsdata.ed.gov/) | Civil rights data (filtered per state) |")
    lines.append("| [NCES FRSS](https://nces.ed.gov/surveys/frss/) | Technology & facilities surveys |\n")

    lines.append("## Raw vs cleaned\n")
    lines.append("- **`data/raw/{state}/`** — files downloaded from state portals.")
    lines.append(
        "- **`data/cleaned/{state}/`** — state-only rows cut from **national** NCES and CRDC "
        "files (additional datasets, not filtered-down copies of raw state files).\n"
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

    catalog_cols = ["state", "category", "description", "url", "local_path", "date_downloaded"]

    def append_catalog_section(title: str, df: pd.DataFrame) -> None:
        lines.append(f"## {title}\n")
        if df.empty:
            lines.append("_No files._\n")
            return
        lines.append(md_table(df[catalog_cols].copy(), catalog_cols))
        lines.append("")

    for slug, label, _ in STATES:
        sub = m[m.state == slug].sort_values(["category", "local_path"])
        append_catalog_section(f"{label} — state downloads (`data/raw/{slug}/`)", sub)

    append_catalog_section("Federal — national downloads (`data/raw/federal/`)", m[m.state == "federal"])

    for slug, label, _ in STATES:
        sub = cleaned_df[cleaned_df.state == slug].sort_values(["category", "local_path"])
        append_catalog_section(f"{label} — cleaned extracts (`data/cleaned/{slug}/`)", sub)

    lines.append("---\n")
    lines.append(
        f"_Catalog generated {datetime.now().strftime('%Y-%m-%d')}. "
        "Machine-readable log: `logs/manifest.csv`._\n"
    )
    SOURCES_OUT.write_text("\n".join(lines), encoding="utf-8")

    total_rows = []
    grand_raw = grand_clean = 0
    for slug, label, _ in STATES:
        raw_n, clean_n = totals_by_state[slug]
        grand_raw += raw_n
        grand_clean += clean_n
        total_rows.append(
            f"| {label} | {raw_n} | {clean_n} | {raw_n + clean_n} |"
        )

    summary = f"""# EOQ Lab — Data Collection Summary

**Prepared for:** Supervisor review  
**Date:** {datetime.now().strftime("%B %d, %Y")}

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

1. **Raw state downloads** (`data/raw/{{state}}/`) — files from state DOE portals, open-data APIs, and web scraping.
2. **Cleaned state extracts** (`data/cleaned/{{state}}/`) — state-only rows from national NCES (schools, F-33 finance) and CRDC topic files.

Raw and cleaned counts are **additive**, not overlapping.

## Files by category

{md_table(combined, ["state", "category", "raw_state_downloads", "cleaned_federal_extracts", "total_datasets"])}

### Totals

| State | Raw (state downloads) | Cleaned (federal extracts) | Combined datasets |
| --- | ---: | ---: | ---: |
{chr(10).join(total_rows)}
| **All four states** | **{grand_raw}** | **{grand_clean}** | **{grand_raw + grand_clean}** |

Plus **{fed_files_on_disk}** federal files on disk under `data/raw/federal/` ({fed_crdc} CRDC zips, {fed_edtech} ed-tech survey files).

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
"""

    SUMMARY_OUT.write_text(summary, encoding="utf-8")

    print(f"Wrote {SOURCES_OUT} ({len(lines)} lines)")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Catalog entries: manifest={len(m)}, cleaned={len(cleaned_df)}")


if __name__ == "__main__":
    main()
