"""
Playwright Report Downloader.

Downloads reports for every configured entity from a web-based reporting
portal, saves them locally organised by date, writes a per-run CSV audit
summary, and copies reports that contain actual data to a pickup folder
for downstream processing.

Usage:
    python report_downloader.py                 # yesterday's reports
    python report_downloader.py --date 20260217 # specific date
    python report_downloader.py --days-back 3   # 3 days ago
    python report_downloader.py --dry-run       # validate config only
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta

from playwright.sync_api import Playwright, sync_playwright

import config
import portal_selectors as sel

# ── CLI ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Playwright Report Downloader",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        type=str,
        metavar="YYYYMMDD",
        help="Target date for reports (e.g. 20260217). Overrides --days-back.",
    )
    group.add_argument(
        "--days-back",
        type=int,
        default=config.DAYS_BACK,
        metavar="N",
        help=f"How many days back to download reports (default: {config.DAYS_BACK}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and create directories without downloading.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed (visible) mode, overriding config.HEADLESS.",
    )
    return parser.parse_args()


args = parse_args()

# ── Date resolution ──────────────────────────────────────────────────────

if args.date:
    try:
        target_date = datetime.strptime(args.date, "%Y%m%d")
    except ValueError:
        print(f"Invalid date format: '{args.date}'. Expected YYYYMMDD (e.g. 20260217).")
        sys.exit(2)
else:
    target_date = datetime.now() - timedelta(days=args.days_back)

target_date_str = target_date.strftime("%d %b %Y")        # UI display format
target_date_yyyymmdd = target_date.strftime("%Y%m%d")
year_folder = target_date.strftime("%Y")
month_folder = target_date.strftime("%b")

# ── Derived paths ────────────────────────────────────────────────────────

DATED_DOWNLOAD_DIR = os.path.join(
    config.DOWNLOAD_DIR, year_folder, month_folder, target_date_yyyymmdd,
)

# ── Logging ──────────────────────────────────────────────────────────────

os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.CSV_SUMMARY_DIR, exist_ok=True)

log_filename = os.path.join(
    config.LOG_DIR,
    f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(),
    ],
)

# ── Helpers ──────────────────────────────────────────────────────────────

def clean_csv_quotes(filepath: str) -> None:
    """Re-write a CSV file with a title row prepended and minimal quoting."""
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(filepath, "r", newline="", encoding=encoding) as f:
                rows = list(csv.reader(f))
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        logging.error("Failed to decode %s with any known encoding", filepath)
        return

    num_cols = len(rows[0]) if rows else 0
    title_row = [config.REPORT_TITLE_ROW] + [""] * (num_cols - 1)
    blank_row = [""] * num_cols
    rows = [title_row, blank_row] + rows

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, quoting=csv.QUOTE_MINIMAL).writerows(rows)


def has_actual_data(filepath: str) -> bool:
    """Return False if the file only contains a 'no data' placeholder."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return config.NO_DATA_MARKER not in f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    logging.warning("Content validation skipped for %s — unreadable", filepath)
    return False


# ── Dry-run mode ─────────────────────────────────────────────────────────

def dry_run() -> None:
    """Validate config and directory creation without touching the browser."""
    logging.info("DRY-RUN MODE — no browser will be launched")

    # Validate credentials
    if not config.PORTAL_EMAIL or not config.PORTAL_PASSWORD:
        logging.warning("PORTAL_EMAIL / PORTAL_PASSWORD not set in .env")
    else:
        logging.info("Credentials found in environment")

    # Validate session file
    if os.path.exists(config.SESSION_FILE):
        logging.info("Session file exists: %s", config.SESSION_FILE)
    else:
        logging.warning("Session file missing: %s — run authenticate.py first", config.SESSION_FILE)

    # Create directories
    os.makedirs(DATED_DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(config.COPY_DIR, exist_ok=True)
    logging.info("Download dir  : %s", DATED_DOWNLOAD_DIR)
    logging.info("Pickup dir    : %s", config.COPY_DIR)

    # Report config
    logging.info("Target date   : %s (%s)", target_date_str, target_date_yyyymmdd)
    logging.info("Entities      : %d configured", len(config.ENTITY_CODES))
    for e in config.ENTITY_CODES:
        logging.info("  - %s", e)
    logging.info("Base URL      : %s", config.BASE_URL)
    logging.info("Headless      : %s", config.HEADLESS)

    logging.info("DRY-RUN complete — config looks valid")


# ── Main download flow ───────────────────────────────────────────────────

def run(playwright: Playwright) -> int:
    """Download reports for every entity. Returns 0 on success, 1 on failure."""
    if not os.path.exists(config.SESSION_FILE):
        logging.critical(
            "Session file not found: %s\n"
            "Run authenticate.py first to save a browser session.",
            config.SESSION_FILE,
        )
        return 1

    os.makedirs(DATED_DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(config.COPY_DIR, exist_ok=True)

    summary_csv_path = os.path.join(
        config.CSV_SUMMARY_DIR,
        f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )
    summary_rows: list[dict] = []

    headless = config.HEADLESS and not args.headed
    browser = playwright.chromium.launch(headless=headless, slow_mo=config.SLOW_MO)
    context = browser.new_context(storage_state=config.SESSION_FILE)
    page = context.new_page()

    for entity in config.ENTITY_CODES:
        start_time = time.perf_counter()
        download_success = False
        data_available = True
        selector_miss = False
        error_details = ""

        try:
            logging.info("Starting extraction for: %s", entity)

            # Step 1: Navigate to portal
            page.goto(config.BASE_URL, wait_until="domcontentloaded", timeout=config.DEFAULT_TIMEOUT)
            if page.get_by_text(sel.ERROR_PAGE_TEXT).is_visible():
                page.reload()

            # Step 2: Re-login if session expired (login page detected)
            login_field = page.get_by_placeholder(sel.LOGIN_EMAIL_PLACEHOLDER)
            if login_field.is_visible():
                logging.warning("Session expired — re-authenticating inline...")
                if not config.PORTAL_EMAIL or not config.PORTAL_PASSWORD:
                    raise ValueError(
                        "PORTAL_EMAIL and PORTAL_PASSWORD must be set in .env"
                    )
                login_field.click()
                login_field.fill(config.PORTAL_EMAIL)
                login_field.press("Tab")
                page.get_by_placeholder(sel.LOGIN_PASSWORD_PLACEHOLDER).fill(config.PORTAL_PASSWORD)
                page.get_by_placeholder(sel.LOGIN_PASSWORD_PLACEHOLDER).press("Enter")
                context.storage_state(path=config.SESSION_FILE)

            # Step 2.5: Detect MFA — cannot proceed unattended
            if page.get_by_text(sel.MFA_PROMPT_TEXT, exact=True).is_visible():
                logging.error(
                    "Portal is requesting MFA — session requires manual re-authentication. "
                    "Run authenticate.py to refresh the session, then re-run this script."
                )
                context.close()
                browser.close()
                return 1

            # Step 3: Navigate to reports section
            page.get_by_role("cell", name=sel.WELCOME_BANNER_PATTERN).get_by_role(
                "link"
            ).nth(1).click()
            page.get_by_role("link", name=sel.REPORTS_LINK_TEXT).click()

            # Step 4: Select entity (force-click to bypass overlapping layers)
            page.locator(sel.ENTITY_ITEM_CSS).filter(
                has_text=entity
            ).get_by_role("link", name=sel.RUN_DASHBOARD_LINK_NAME).filter(
                has=page.locator("visible=true")
            ).first.click(force=True)

            # Step 5: Date filter — clear then select target date
            page.locator(sel.DATE_FILTER_REMOVE_ALL_ID).get_by_role(
                "img", name="Remove All"
            ).click()

            date_selector = page.get_by_text(target_date_str, exact=True)
            try:
                date_selector.wait_for(state="visible", timeout=5000)
                date_selector.click()
            except Exception:
                logging.error("[%s] Date '%s' not found in filter — skipping", entity, target_date_str)
                data_available = False
                error_details = "Date not found"
                continue

            page.locator(sel.DATE_FILTER_ADD_ID).get_by_role(
                "img", name="Add"
            ).click()

            # Step 6: Run dashboard and wait for load
            page.get_by_role("button", name=sel.RUN_DASHBOARD_LINK_NAME).click()
            page.wait_for_load_state("networkidle")

            if page.locator(sel.FILTER_PANEL_CLOSE_CSS).is_visible():
                page.locator(sel.FILTER_PANEL_CLOSE_CSS).click()

            # Step 7: Check for empty data
            if page.get_by_text(config.NO_DATA_MARKER).is_visible():
                data_available = False
                logging.warning(
                    "[%s] No data for %s — downloading empty file for audit trail",
                    entity, target_date_str,
                )

            # Step 8: Open export menu (retry; portal menu can be slow)
            export_item = page.locator(sel.CONTEXT_MENU_ITEM_CSS).filter(
                has_text=sel.EXPORT_MENU_TEXT
            )
            menu_opened = False
            for attempt in range(config.MENU_RETRY_LIMIT):
                logging.debug("Context menu attempt %d...", attempt + 1)
                page.get_by_label(sel.CONTEXT_MENU_LABEL).click(force=True)
                page.wait_for_timeout(config.MENU_RETRY_DELAY)
                if export_item.is_visible():
                    menu_opened = True
                    break

            if not menu_opened:
                raise RuntimeError(f"[{entity}] Export menu not found after {config.MENU_RETRY_LIMIT} attempts")

            # Step 9: Export as CSV via popup
            export_item.hover()
            data_option = page.get_by_role("menuitem", name=sel.EXPORT_DATA_MENUITEM_NAME, exact=True)
            data_option.wait_for(state="visible")

            try:
                with page.expect_popup() as popup_info:
                    data_option.click()
                popup = popup_info.value

                with popup.expect_download(timeout=config.EXPORT_TIMEOUT) as download_info:
                    download_btn = popup.get_by_role("button", name=sel.DOWNLOAD_BUTTON_NAME)
                    if download_btn.is_visible():
                        download_btn.click()

                download = download_info.value
                entity_clean = entity.rsplit("-", 1)[0]
                filename = f"{config.REPORT_PREFIX}_{entity_clean}_{target_date_yyyymmdd}.csv"
                filepath = os.path.join(DATED_DOWNLOAD_DIR, filename)

                download.save_as(filepath)
                clean_csv_quotes(filepath)

                if not has_actual_data(filepath):
                    if data_available:
                        selector_miss = True
                        logging.warning(
                            "[%s] Content check corrected data_available to False — "
                            "'No data' text found in %s.",
                            entity, filename,
                        )
                    data_available = False

                download_success = True
                logging.info("[%s] Downloaded: %s", entity, filename)
                popup.close()

            except Exception as e:
                error_details = str(e)
                logging.error("[%s] Download failed: %s", entity, e)

            # Reset view for next iteration
            page.locator(sel.RESET_VIEW_CSS).click()

        except Exception as e:
            error_details = str(e)
            logging.error("[%s] Unexpected error: %s", entity, e)

        finally:
            entity_clean = entity.rsplit("-", 1)[0]
            execution_time = round(time.perf_counter() - start_time, 2)
            summary_rows.append({
                "entity_code": entity,
                "filename": f"{config.REPORT_PREFIX}_{entity_clean}_{target_date_yyyymmdd}.csv",
                "download_success": download_success,
                "data_available": data_available,
                "selector_miss": selector_miss,
                "execution_time_sec": execution_time,
                "error_details": error_details,
                "report_date": target_date_yyyymmdd,
            })

    # ── Write audit CSV ──────────────────────────────────────────────────
    fieldnames = [
        "entity_code", "filename", "download_success", "data_available",
        "selector_miss", "execution_time_sec", "error_details", "report_date",
    ]
    if summary_rows:
        with open(summary_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        logging.info("Summary written to %s", summary_csv_path)

    # ── Copy reports with data to pickup folder ──────────────────────────
    copied_files: list[str] = []
    copy_errors: list[tuple[str, str]] = []
    seen: set[str] = set()

    for row in summary_rows:
        if row["download_success"] and row["data_available"]:
            fname = row["filename"]
            if fname in seen:
                logging.warning("Duplicate entry for %s — skipping", fname)
                continue
            seen.add(fname)
            src = os.path.join(DATED_DOWNLOAD_DIR, fname)
            dst = os.path.join(config.COPY_DIR, fname)
            try:
                shutil.copy2(src, dst)
                copied_files.append(fname)
                logging.info("Copied %s to %s", fname, config.COPY_DIR)
            except Exception as e:
                copy_errors.append((fname, str(e)))
                logging.error("Failed to copy %s: %s", fname, e)

    # ── End-of-run summary ───────────────────────────────────────────────
    total = len(summary_rows)
    downloaded = sum(1 for r in summary_rows if r["download_success"])
    no_data = sum(1 for r in summary_rows if r["download_success"] and not r["data_available"])
    failed = sum(1 for r in summary_rows if not r["download_success"])
    misses = [r["filename"] for r in summary_rows if r.get("selector_miss")]
    errors = [(r["entity_code"], r["error_details"]) for r in summary_rows if r["error_details"]]

    logging.info("=" * 60)
    logging.info("  Run Summary — %s", target_date_str)
    logging.info("=" * 60)
    logging.info("  Entities processed   : %d", total)
    logging.info("  Files downloaded     : %d", downloaded)
    logging.info("  Copied to pickup     : %d", len(copied_files))
    logging.info("  No data (skipped)    : %d", no_data)
    logging.info("  Failed downloads     : %d", failed)
    if misses:
        logging.warning("  Selector misses caught by content check (%d):", len(misses))
        for m in misses:
            logging.warning("    - %s", m)
    if copy_errors:
        logging.error("  Copy errors (%d):", len(copy_errors))
        for fname, err in copy_errors:
            logging.error("    - %s: %s", fname, err)
    if errors:
        logging.error("  Extraction errors (%d):", len(errors))
        for ent, err in errors:
            logging.error("    - %s: %s", ent, err)
    logging.info("  Summary CSV          : %s", summary_csv_path)
    logging.info("=" * 60)

    context.close()
    browser.close()

    return 1 if failed > 0 else 0


# ── Entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if args.dry_run:
        dry_run()
        sys.exit(0)

    with sync_playwright() as pw:
        sys.exit(run(pw))
