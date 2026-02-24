# Script Auditor

A Flask + Playwright web app and CLI tool that detects all JavaScript scripts loaded on a webpage (including GTM-injected ones) and identifies their vendor.

## Cursor Cloud specific instructions

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Flask dev server | `source venv/bin/activate && python3 app.py` | 7070 | Threaded dev server; serves UI and SSE audit API |
| CLI audit | `source venv/bin/activate && python3 audit_scripts.py <url> --verbose` | N/A | Standalone CLI for single/batch URL auditing |

### Development notes

- **Virtual environment**: Always activate with `source venv/bin/activate` before running any Python commands.
- **Port**: The app runs on port **7070** (not 8080 as the README states in some places — the README has an inconsistency).
- **Playwright Chromium**: Must be installed in the venv via `python3 -m playwright install chromium`. The Chromium binary lives in `~/.cache/ms-playwright/`. If Playwright is upgraded, re-run this command.
- **No database or external services needed**: The app is entirely stateless and in-memory.
- **`--no-sandbox` flag**: The Flask app already passes `--no-sandbox` to Chromium (required in container/CI environments). The CLI does not; if a CLI test fails with a sandbox error, use the web UI or add `--no-sandbox` to the Chromium launch args in `audit_scripts.py`.
- **No linter or test framework configured**: The codebase has no linting config or automated tests.
- **Gunicorn** is production-only (`gunicorn.conf.py`); for development, use `python3 app.py` directly.
