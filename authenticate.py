"""
Interactive session (re-)authentication script.

Run this whenever the saved browser session expires or after a password
change.  The script opens a real browser so the operator
can complete the full login flow — including any MFA / OTP step — then saves
the resulting session state for unattended use by report_downloader.py.
"""

import json
import os
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from config import AUTH_URL, SESSION_DIR, SESSION_FILE, SESSION_METADATA_FILE, SESSION_LIFETIME_DAYS


def authenticate() -> bool:
    """Open the portal, let the operator log in, and persist the session."""

    print("\n" + "=" * 70)
    print("SESSION RE-AUTHENTICATION")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Open the portal in a browser")
    print("  2. Let you log in (including MFA/OTP if required)")
    print("  3. Save your new session for automated runs")
    print(f"\nSession lifetime depends on your portal (configured: ~{SESSION_LIFETIME_DAYS} days).")
    print("=" * 70)

    input("\nPress ENTER to begin re-authentication...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=["--start-maximized"],
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()

        print("\nOpening portal...")
        page.goto(AUTH_URL)

        print("\n" + "=" * 70)
        print("PLEASE LOG IN USING THE BROWSER WINDOW")
        print("=" * 70)
        print("\nSteps:")
        print("  1. Enter your username / email")
        print("  2. Enter your password")
        print("  3. Complete MFA / OTP if prompted")
        print("  4. Wait until you see the main portal page")
        print("=" * 70)

        input("\nPress ENTER after you have completed login...")

        time.sleep(3)  # let the page settle

        final_url = page.url
        print(f"\nCurrent URL: {final_url}")

        # --- Verify login (basic heuristic) ---
        success = "login" not in final_url.lower()

        if not success:
            print("\nWARNING: Could not verify successful login.")
            proceed = input("   Continue saving session anyway? (yes/no): ")
            if proceed.strip().lower() != "yes":
                print("\nRe-authentication cancelled.")
                browser.close()
                return False

        # --- Back up previous session ---
        if os.path.exists(SESSION_FILE):
            backup = os.path.join(
                SESSION_DIR,
                f"session_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            os.rename(SESSION_FILE, backup)
            print(f"\nOld session backed up to: {backup}")

        # --- Save new session ---
        print("\nSaving new session...")
        os.makedirs(SESSION_DIR, exist_ok=True)
        storage_state = context.storage_state()

        with open(SESSION_FILE, "w") as f:
            json.dump(storage_state, f, indent=2)

        metadata = {
            "authenticated_at": datetime.now().isoformat(),
            "authenticated_by": os.getenv("USERNAME", os.getenv("USER", "unknown")),
            "expires_approximately": datetime.now().timestamp() + (SESSION_LIFETIME_DAYS * 86400),
            "final_url": final_url,
            "cookie_count": len(storage_state.get("cookies", [])),
        }
        with open(SESSION_METADATA_FILE, "w") as f:
            json.dump(metadata, f, indent=2)

        print("New session saved successfully!")

        print("\n" + "=" * 70)
        print("RE-AUTHENTICATION COMPLETE")
        print("=" * 70)
        print(f"\n  Authenticated at : {metadata['authenticated_at']}")
        print(f"  Expected validity: ~{SESSION_LIFETIME_DAYS} days (varies by portal)")
        print(f"  Cookies saved    : {metadata['cookie_count']}")
        print(f"\nRe-run this script when the session expires.")
        print("=" * 70)

        time.sleep(3)
        browser.close()
        return True


if __name__ == "__main__":
    try:
        ok = authenticate()
        sys.exit(0 if ok else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\nError: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
