# Enterprise Portal Report Downloader (Playwright + Python)

A production-grade browser automation template that downloads reports from a
web-based enterprise portal, handles session persistence and MFA handoff,
retries flaky UI elements, writes an audit CSV summary, and copies results to
a downstream pickup folder — all driven by Playwright and plain Python.

---

## What this demonstrates

- **Session lifecycle management** — save, reuse, and refresh browser sessions
  across runs; detect expiry and MFA prompts automatically.
- **MFA / OTP reauth workflow** — a dedicated `authenticate.py` script lets an
  operator complete MFA interactively, then saves the session for unattended use.
- **Robust selector strategy** — all selectors live in `selectors.py`, clearly
  marked as examples to customise, with role/label preferred over fragile CSS.
- **Retry logic for flaky menus** — configurable retry loop for context menus
  that are slow to render.
- **Download handling** — captures downloads triggered via popups, saves with
  structured filenames, and validates content.
- **Audit CSV summary** — every run produces a CSV with per-entity success,
  data availability, timing, and error details.
- **Idempotent file copy** — only reports with actual data are copied to the
  pickup folder; duplicates are detected and skipped.
- **Date parameterisation** — `--date YYYYMMDD` or `--days-back N` CLI flags.
- **Dry-run mode** — `--dry-run` validates config and directory creation
  without launching a browser.
- **Proper exit codes** — 0 on success, non-zero on failure.

---

## Project structure

```
enterprise-portal-downloader/
├── report_downloader.py    # Main script — downloads reports for all entities
├── authenticate.py         # Interactive session capture (MFA-safe)
├── config.py               # All configuration in one place
├── portal_selectors.py     # UI selectors (customise for your portal)
├── requirements.txt        # Python dependencies
├── .env.example            # Template for credentials
├── SECURITY.md             # What must never be committed
│
├── auth_state/             # Saved browser session (git-ignored)
├── logs/                   # Per-run log files (git-ignored)
├── csv_summary/            # Per-run audit CSVs (git-ignored)
├── downloaded_reports/     # Reports organised by YYYY/Mon/YYYYMMDD (git-ignored)
└── pickup_folder/          # Reports with data, for downstream pickup (git-ignored)
```

---

## Quick start

### 1. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

> If Playwright fails due to an SSL error behind a corporate proxy, set
> `NODE_TLS_REJECT_UNAUTHORIZED=0` and retry.

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env with your real portal email and password
```

### 4. Capture your session

```bash
python authenticate.py
```

Log in when the browser opens (including MFA/OTP), then press ENTER.
The session is saved to `auth_state/session.json`.

### 5. Run the downloader

```bash
python report_downloader.py              # yesterday's reports
python report_downloader.py --date 20260217   # specific date
python report_downloader.py --days-back 3     # 3 days ago
python report_downloader.py --dry-run         # validate config only
python report_downloader.py --headed          # watch the browser
```

---

## How to adapt to your portal

1. **`config.py`** — set `BASE_URL`, `AUTH_URL`, your entity list
   (`ENTITY_CODES`), directory paths, and timeouts.
2. **`portal_selectors.py`** — replace every selector with ones that match your
   portal's DOM. Use `playwright codegen <URL>` to discover them.
3. **`report_downloader.py`** — adjust the step-by-step flow (login detection,
   navigation, date filtering, export) to match your portal's UI.
4. **`.env`** — set your credentials.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Session file not found" | Run `authenticate.py` first. |
| "Portal is requesting MFA" | Session expired. Run `authenticate.py` again. |
| "Date not found in filter" | The report date has no data in the portal. |
| `download_success: False` | Check `error_details` in the CSV summary or the log file. |

---

## Configuration reference

All tunables live in `config.py`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `BASE_URL` | Portal reports page | `https://portal.example/reports` |
| `AUTH_URL` | Login / MFA page | `https://portal.example/login` |
| `ENTITY_CODES` | List of entities to process | 4 example placeholders |
| `HEADLESS` | Run browser without UI | `True` |
| `DAYS_BACK` | Default days back | `1` (yesterday) |
| `DOWNLOAD_DIR` | Report archive root | `downloaded_reports` |
| `COPY_DIR` | Downstream pickup folder | `pickup_folder` |
