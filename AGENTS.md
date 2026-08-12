# Script Auditor

A Flask + Playwright web app and CLI tool that detects all JavaScript scripts loaded on a webpage (including GTM-injected ones) and identifies their vendor.

## Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Flask dev server | `source venv/bin/activate && python3 app.py` | 7070 | Threaded dev server; serves UI and SSE audit API |
| Launcher | `source venv/bin/activate && python3 start.py` | 7070 | Bootstraps venv & starts Flask app |
| CLI audit | `source venv/bin/activate && python3 audit_scripts.py <url> --verbose` | N/A | Standalone CLI for single/batch URL auditing |

## Development notes

- **Virtual environment**: Always activate with `source venv/bin/activate` before running any Python commands.
- **Port**: Flask app runs on **7070**.
- **Playwright Chromium**: Must be installed via `python3 -m playwright install chromium`. Binary lives in `~/.cache/ms-playwright/`.
- **System Chrome**: Uses `channel="chrome"` to use system Google Chrome instead of bundled Chromium.
- **Vendor database**: `vendor_db.json` contains 1200+ domain→vendor mappings from DuckDuckGo Tracker Radar. Rebuild with `python3 build_vendor_db.py`.
- **User interactions**: Auto-clicks cookie consent banners and scrolls page to trigger lazy-loaded scripts. Disable with `--no-click-consent` or `--no-scroll`.
- **No database**: The app is entirely stateless and in-memory.
- **`--no-sandbox` flag**: Flask app passes `--no-sandbox` to Chromium (required in containers).
- **No linter or tests**: The codebase has no linting config or automated tests.
- **Gunicorn** is production-only; for development, use `python3 app.py` directly.
