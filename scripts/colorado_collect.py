"""Colorado-specific discovery seeds and Socrata configuration."""

from __future__ import annotations

SOCRATA_BASE = "https://data.colorado.gov"

# Catalog search terms — combined with attribution filter for CDE datasets
SOCRATA_SEARCH_QUERIES = [
    "CDE",
    "Department of Education",
    "K-12",
    "school district",
    "graduation",
    "assessment CMAS",
    "enrollment",
    "discipline",
    "teacher",
    "finance education",
    "TCAP",
    "PSAT",
]

SOCRATA_ATTRIBUTION_KEYWORDS = (
    "CDE",
    "Department of Education",
    "Colorado Department of Education",
)

# CDE pages with direct XLS/XLSX/CSV/ZIP download links (BeautifulSoup harvest)
HTML_SEED_URLS = [
    "https://ed.cde.state.co.us/accountability/data-tools/data-files",
    "https://ed.cde.state.co.us/accountability/data-tools",
    "https://www.cde.state.co.us/cdereval",
    "https://www.cde.state.co.us/schoolview",
    "https://www.cde.state.co.us/assessment/cmas-dataandresults",
    "https://www.cde.state.co.us/assessment/cmas",
    "https://www.cde.state.co.us/assessment/psat",
]

# Hand-picked stable files (Phase 1 proof-of-concept)
DIRECT_DOWNLOADS = [
    {
        "dataset_title": "CDE 2025 Preliminary District Performance Ratings Over Time",
        "url": "https://ed.cde.state.co.us/fs/resource-manager/view/bdbfed5c-32a6-43c1-a55d-cbc0c96c172d",
        "description": "Colorado: CDE 2025 preliminary district ratings (accountability)",
        "category": "test_scores",
        "dest_filename": "DPF2025_PreliminaryRatingsOverTime.xlsx",
        "format": "XLSX",
    },
    {
        "dataset_title": "CDE 2025 Preliminary School Performance Ratings Over Time",
        "url": "https://ed.cde.state.co.us/fs/resource-manager/view/05ef35b0-dfd6-47fd-99af-2933bb35214b",
        "description": "Colorado: CDE 2025 preliminary school ratings (accountability)",
        "category": "test_scores",
        "dest_filename": "SPF2025_PreliminaryRatingsOverTime.xlsx",
        "format": "XLSX",
    },
]
