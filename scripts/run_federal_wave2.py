"""Wave 2: School Pulse Panel + optional 2021-22 CRDC zip + re-extract CRDC topics.

Run from project root:

    python scripts/run_federal_wave2.py

Large optional download (~800 MB):

    python scripts/run_federal_wave2.py --with-crdc-2122
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from federal_collect import (  # noqa: E402
    discover_spp_themed_files,
    download_crdc_public_zip,
    download_to_path,
    ensure_federal_layout,
    extract_crdc_zips,
    refresh_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Federal wave 2: SPP + CRDC 2021-22")
    parser.add_argument(
        "--with-crdc-2122",
        action="store_true",
        help="Download 2021-22 CRDC public-use zip (~800 MB) before extracting",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip CRDC zip extraction (downloads only)",
    )
    args = parser.parse_args()

    paths = ensure_federal_layout(PROJECT)
    download_log = paths["logs_dir"] / "download_log.jsonl"
    manifest_csv = paths["logs_dir"] / "manifest.csv"

    if args.with_crdc_2122:
        print("=== Step 1: Download 2021-22 CRDC zip (~800 MB — may take several minutes) ===")
        record = download_crdc_public_zip(
            "2021-22",
            paths,
            download_log,
            PROJECT,
        )
        print(f"  -> {record['status']}: {record.get('local_path', record.get('error', ''))}")
    else:
        print("=== Step 1: Skipped 2021-22 CRDC zip (pass --with-crdc-2122 to download) ===")

    print("\n=== Step 2: School Pulse Panel — civil rights + ed-tech topics ===")
    spp_df = discover_spp_themed_files()
    print(f"SPP files to download: {len(spp_df)}")
    spp_records = []
    for _, row in spp_df.iterrows():
        category = str(row.get("category", "other"))
        dest_root = paths["spp_root"] / ("civil_rights" if category == "discipline" else "edtech")
        dest_path = dest_root / row["dest_filename"]
        print(f"  {row['dest_filename']}")
        record = download_to_path(
            row["url"],
            dest_path,
            description=row["description"],
            category=category,
            download_log=download_log,
            project_root=PROJECT,
        )
        if record["status"] == "failed":
            print(f"    -> FAILED: {str(record.get('error', ''))[:80]}")
        else:
            print(f"    -> {record['status']}")
        spp_records.append(record)

    if not args.skip_extract:
        print("\n=== Step 3: Extract CRDC topic CSVs from all zips on disk ===")
        extract_records = extract_crdc_zips(
            PROJECT,
            paths["crdc_extracted_root"],
            download_log,
        )
        print(
            f"  extracted: {sum(1 for r in extract_records if r['status'] == 'extracted')}, "
            f"skipped: {sum(1 for r in extract_records if r['status'] == 'skipped_exists')}, "
            f"failed: {sum(1 for r in extract_records if r['status'] == 'failed')}"
        )
    else:
        print("\n=== Step 3: Skipped CRDC extraction ===")

    print("\n=== Step 4: Refresh manifest ===")
    manifest = refresh_manifest(download_log, manifest_csv)
    fed = manifest[manifest["state"] == "federal"] if not manifest.empty else pd.DataFrame()

    summary = [
        {"location": "data/raw/federal/spp/", "files": sum(1 for p in paths["spp_root"].rglob("*") if p.is_file())},
        {
            "location": "data/raw/federal/crdc_extracted/",
            "files": sum(1 for p in paths["crdc_extracted_root"].rglob("*") if p.is_file()),
        },
        {"location": "data/raw/federal/ (all)", "files": sum(1 for p in paths["federal_root"].rglob("*") if p.is_file())},
    ]
    print(pd.DataFrame(summary).to_string(index=False))
    if not fed.empty:
        print("\nFederal manifest rows by category:")
        print(fed.groupby("category").size())
    print(f"\nDone. Manifest: {manifest_csv}")
    print("\nOptional next: python scripts/generate_docs.py")


if __name__ == "__main__":
    main()
