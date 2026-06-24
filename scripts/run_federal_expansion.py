"""Phase 3 federal expansion: extract CRDC zips + download new FRSS surveys.

Run from project root:
    python scripts/run_federal_expansion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from federal_collect import (  # noqa: E402
    discover_federal_expansion_downloads,
    download_to_path,
    edtech_dest_filename,
    ensure_federal_layout,
    extract_crdc_zips,
    refresh_manifest,
)


def main() -> None:
    paths = ensure_federal_layout(PROJECT)
    download_log = paths["logs_dir"] / "download_log.jsonl"
    manifest_csv = paths["logs_dir"] / "manifest.csv"

    print("=== Step A: Extract CRDC topic files from zips on disk ===")
    zips = list(paths["project_root"].glob("data/raw/federal/**/*.zip"))
    crdc_zips = [p for p in zips if "crdc" in p.name.lower()]
    print(f"CRDC zips found: {len(crdc_zips)}")
    for p in crdc_zips:
        print(f"  {p.relative_to(PROJECT)}")

    extract_records = extract_crdc_zips(
        PROJECT,
        paths["crdc_extracted_root"],
        download_log,
    )
    extracted = sum(1 for r in extract_records if r["status"] == "extracted")
    skipped = sum(1 for r in extract_records if r["status"] == "skipped_exists")
    failed = sum(1 for r in extract_records if r["status"] == "failed")
    print(f"Extracted: {extracted}, skipped: {skipped}, failed: {failed}")
    print(f"Output folder: {paths['crdc_extracted_root'].relative_to(PROJECT)}")

    print("\n=== Step B: Download new FRSS surveys (direct NCES URLs) ===")
    catalog = discover_federal_expansion_downloads()
    print(f"Downloads queued: {len(catalog)}")
    dl_records = []
    for _, row in catalog.iterrows():
        category = str(row.get("category", "other"))
        dest_root = paths["federal_root"] / category
        if category == "other":
            dest_root = paths["edtech_root"]
        fname = edtech_dest_filename(row)
        dest_path = dest_root / fname
        print(f"  {fname}")
        record = download_to_path(
            row["url"],
            dest_path,
            description=row["description"],
            category=category,
            download_log=download_log,
            project_root=PROJECT,
        )
        status = record["status"]
        if status == "failed":
            print(f"    -> FAILED: {record.get('error', '')[:80]}")
        elif status == "skipped_exists":
            print("    -> skipped (exists)")
        else:
            print(f"    -> {status}")
        dl_records.append(record)

    downloaded = sum(1 for r in dl_records if r["status"] == "downloaded")
    print(f"New downloads: {downloaded}")

    print("\n=== Step C: Refresh manifest ===")
    manifest = refresh_manifest(download_log, manifest_csv)
    fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

    summary = [
        {
            "location": "data/raw/federal/crdc_extracted/",
            "files": sum(1 for p in paths["crdc_extracted_root"].rglob("*") if p.is_file()),
        },
        {
            "location": "data/raw/federal/edtech/",
            "files": sum(1 for p in paths["edtech_root"].rglob("*") if p.is_file()),
        },
        {
            "location": "data/raw/federal/ (all)",
            "files": sum(1 for p in paths["federal_root"].rglob("*") if p.is_file()),
        },
    ]
    print(pd.DataFrame(summary).to_string(index=False))
    if not fed.empty:
        print("\nFederal manifest rows by category:")
        print(fed.groupby("category").size())
    print(f"\nManifest: {manifest_csv}")


if __name__ == "__main__":
    main()
