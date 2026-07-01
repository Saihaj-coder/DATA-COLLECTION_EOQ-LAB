"""Run Colorado + Texas state collection (same logic as the notebook)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import colorado_collect
import texas_collect
from federal_collect import refresh_manifest
from state_collect import (
    STATE_ABBRS,
    STATE_SLUGS,
    discover_html_seed_pages,
    discover_socrata_datasets,
    direct_download_catalog,
    download_state_rows,
    ensure_state_layout,
    filter_crdc_extracted_for_state,
    filter_nces_ccd_for_state,
    filter_nces_f33_for_state,
    state_collection_summary,
)

SECONDS_BETWEEN_DOWNLOADS = 0.5
MAX_TX_PEIMS_ZIP_DOWNLOADS = 0
SOCRATA_EXPORTABLE_ONLY = True
SOCRATA_MAX_PER_QUERY = 200
SECONDS_BETWEEN_SOCRATA_CHECKS = 0.3
DOWNLOAD_ARCGIS_CSV = True


def summarize(records: list[dict], label: str) -> None:
    print(
        f"{label} — downloaded: {sum(1 for r in records if r['status'] == 'downloaded')}, "
        f"skipped: {sum(1 for r in records if r['status'] == 'skipped_exists')}, "
        f"failed: {sum(1 for r in records if r['status'] == 'failed')}"
    )


def main() -> None:
    paths = ensure_state_layout(PROJECT_ROOT, STATE_SLUGS)
    download_log = paths["logs_dir"] / "download_log.jsonl"
    manifest_csv = paths["logs_dir"] / "manifest.csv"

    print("=== Phase 1: Direct downloads ===")
    phase1 = direct_download_catalog("colorado", colorado_collect.DIRECT_DOWNLOADS)
    phase1 = __import__("pandas").concat(
        [phase1, direct_download_catalog("texas", texas_collect.DIRECT_DOWNLOADS)],
        ignore_index=True,
    )
    summarize(download_state_rows(phase1, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS), "Phase 1")

    print("\n=== Phase 2: Colorado Socrata ===")
    co_socrata = discover_socrata_datasets(
        colorado_collect.SOCRATA_BASE,
        colorado_collect.SOCRATA_SEARCH_QUERIES,
        "colorado",
        attribution_keywords=colorado_collect.SOCRATA_ATTRIBUTION_KEYWORDS,
        max_per_query=SOCRATA_MAX_PER_QUERY,
        exportable_only=SOCRATA_EXPORTABLE_ONLY,
        seconds_between_checks=SECONDS_BETWEEN_SOCRATA_CHECKS,
    )
    co_socrata.to_csv(paths["logs_dir"] / "co_discovered_links.csv", index=False)
    print(f"Discovered (exportable): {len(co_socrata)}")
    summarize(
        download_state_rows(co_socrata, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS),
        "CO Socrata",
    )

    print("\n=== Phase 3: Texas Socrata ===")
    tx_socrata = discover_socrata_datasets(
        texas_collect.SOCRATA_BASE,
        texas_collect.SOCRATA_SEARCH_QUERIES,
        "texas",
        attribution_keywords=texas_collect.SOCRATA_ATTRIBUTION_KEYWORDS,
        max_per_query=SOCRATA_MAX_PER_QUERY,
        exportable_only=SOCRATA_EXPORTABLE_ONLY,
        seconds_between_checks=SECONDS_BETWEEN_SOCRATA_CHECKS,
    )
    tx_socrata.to_csv(paths["logs_dir"] / "tx_discovered_links.csv", index=False)
    print(f"Discovered (exportable): {len(tx_socrata)}")
    summarize(
        download_state_rows(tx_socrata, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS),
        "TX Socrata",
    )

    print("\n=== Phase 4: Colorado HTML ===")
    co_html = discover_html_seed_pages(colorado_collect.HTML_SEED_URLS, "colorado", page_label="CDE")
    print(f"Discovered: {len(co_html)}")
    summarize(
        download_state_rows(co_html, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS),
        "CO HTML",
    )

    print("\n=== Phase 5: Texas HTML (PEIMS cap =", MAX_TX_PEIMS_ZIP_DOWNLOADS, ") ===")
    tx_html = discover_html_seed_pages(texas_collect.HTML_SEED_URLS, "texas", page_label="TEA")
    tx_html = texas_collect.limit_texas_peims_downloads(tx_html, MAX_TX_PEIMS_ZIP_DOWNLOADS)
    print(f"Downloading: {len(tx_html)} links")
    summarize(
        download_state_rows(tx_html, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS),
        "TX HTML",
    )

    print("\n=== Phase 6a: Texas ArcGIS catalog ===")
    tx_arcgis = texas_collect.discover_tea_arcgis_items(max_items=200)
    tx_arcgis.to_csv(paths["logs_dir"] / "tx_arcgis_discovered.csv", index=False)
    print(f"Cataloged: {len(tx_arcgis)} items")

    if DOWNLOAD_ARCGIS_CSV:
        print("\n=== Phase 6b: Texas ArcGIS CSV downloads ===")
        tx_arcgis_catalog = texas_collect.build_arcgis_download_catalog(tx_arcgis)
        print(f"CSV layers queued: {len(tx_arcgis_catalog)}")
        summarize(
            download_state_rows(tx_arcgis_catalog, PROJECT_ROOT, download_log, seconds_between=SECONDS_BETWEEN_DOWNLOADS),
            "TX ArcGIS",
        )

    print("\n=== Phase 7: Federal filter CO/TX ===")
    for state_slug in STATE_SLUGS:
        abbr = STATE_ABBRS[state_slug]
        print(f"\n{state_slug.title()} ({abbr})")
        print("  NCES schools:", filter_nces_ccd_for_state(PROJECT_ROOT, state_slug, abbr, download_log))
        print("  NCES F-33:", filter_nces_f33_for_state(PROJECT_ROOT, state_slug, abbr, download_log))
        crdc = filter_crdc_extracted_for_state(PROJECT_ROOT, state_slug, abbr, download_log)
        print(
            f"  CRDC: {sum(1 for r in crdc if r.get('status')=='written')} written, "
            f"{sum(1 for r in crdc if r.get('status')=='skipped_exists')} skipped"
        )

    print("\n=== Phase 8: Summary ===")
    refresh_manifest(download_log, manifest_csv)
    for state_slug in STATE_SLUGS:
        print(f"\n{state_slug.upper()}:")
        print(state_collection_summary(PROJECT_ROOT, state_slug).to_string(index=False))


if __name__ == "__main__":
    main()
