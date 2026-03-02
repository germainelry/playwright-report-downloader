"""
Centralized configuration for the Playwright Report Downloader.

Adapt these values to match your target portal, entity list, and directory layout.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Portal connection
# ---------------------------------------------------------------------------
# Replace with the real URL of the portal you are automating.
BASE_URL = "https://portal.example/reports"

# Authentication URL (where the manual login/MFA flow begins).
AUTH_URL = "https://portal.example/login"

# Environment-variable names that hold credentials (loaded from .env).
PORTAL_EMAIL: str = os.getenv("PORTAL_EMAIL", "")
PORTAL_PASSWORD: str = os.getenv("PORTAL_PASSWORD", "")

# ---------------------------------------------------------------------------
# Session / auth state
# ---------------------------------------------------------------------------
SESSION_DIR = "auth_state"
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")
SESSION_METADATA_FILE = os.path.join(SESSION_DIR, "session_metadata.json")

# Approximate session lifetime (days). Varies by portal — adjust to match yours.
# Used only for display purposes in authenticate.py.
SESSION_LIFETIME_DAYS = 30

# ---------------------------------------------------------------------------
# Entities to process
# ---------------------------------------------------------------------------
# Each entry is "<ENTITY_CODE>-<sequence>".  The sequence suffix is stripped
# before it is used in filenames — it exists only to disambiguate duplicates
# in the portal's UI.  Replace these with your own entity codes.
ENTITY_CODES: list[str] = [
    "ENTITY_AAA-1",
    "ENTITY_BBB-2",
    "ENTITY_CCC-3",
    "ENTITY_DDD-4",
]

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
# Where downloaded reports are saved (organised by year/month/date).
DOWNLOAD_DIR = "downloaded_reports"

# Where reports with actual data are copied for downstream pickup.
COPY_DIR = "pickup_folder"

# Logs and per-run CSV summaries.
LOG_DIR = "logs"
CSV_SUMMARY_DIR = "csv_summary"

# ---------------------------------------------------------------------------
# Browser / Playwright settings
# ---------------------------------------------------------------------------
HEADLESS: bool = True  # Set False to watch the browser during development.
SLOW_MO: int = 0       # Milliseconds to slow down each Playwright action.
DEFAULT_TIMEOUT: int = 60_000   # Navigation timeout (ms).
EXPORT_TIMEOUT: int = 60_000    # Download wait timeout (ms).
MENU_RETRY_LIMIT: int = 5       # Max attempts to open a stubborn context menu.
MENU_RETRY_DELAY: int = 1_000   # Delay between menu-open retries (ms).

# ---------------------------------------------------------------------------
# Report settings
# ---------------------------------------------------------------------------
DAYS_BACK: int = 1  # Default: download yesterday's reports.
REPORT_PREFIX = "RPT"  # Prefix used in downloaded filenames, e.g. RPT_ENTITY_20260301.csv
REPORT_TITLE_ROW = "Activity Report"  # Title prepended as Row 1 in cleaned CSVs.
NO_DATA_MARKER = "No data returned for this view"  # Text the portal shows when empty.
