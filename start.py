#!/usr/bin/env python3
"""
start.py — One-command launcher for Script Auditor.

Ensures the virtualenv exists with all dependencies (and Playwright's Chromium)
installed, then starts both the Flask (V1) and Streamlit (V2) apps together.

Just run:

    python3 start.py

It works whether or not the venv is activated — it bootstraps what's missing
and re-executes itself under the venv's Python.
"""

import os
import shutil
import signal
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
VENV_BIN = os.path.join(VENV_DIR, "bin")
VENV_PY = os.path.join(VENV_BIN, "python3")
REQUIREMENTS = os.path.join(SCRIPT_DIR, "requirements.txt")


def _running_in_venv():
    return os.path.abspath(sys.executable) == os.path.abspath(VENV_PY)


def _deps_installed():
    return subprocess.run(
        [VENV_PY, "-c", "import flask, streamlit, playwright"],
        cwd=SCRIPT_DIR,
    ).returncode == 0


def _system_chrome():
    """The apps launch Chrome via channel="chrome", so a system Chrome is
    enough to run audits even where Playwright's bundled Chromium isn't."""
    return any(
        shutil.which(b)
        for b in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
    )


def _chromium_installed():
    code = (
        "import os, sys\n"
        "from playwright.sync_api import sync_playwright\n"
        "with sync_playwright() as p:\n"
        "    sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)\n"
    )
    return subprocess.run([VENV_PY, "-c", code], cwd=SCRIPT_DIR).returncode == 0


def _browser_available():
    return _system_chrome() or _chromium_installed()


def ensure_venv():
    """Create the venv and install deps/Chromium if needed, then re-exec
    this script under the venv's Python so child processes inherit it."""
    if not os.path.exists(VENV_PY):
        print("Creating virtualenv (venv/)...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

    if not _deps_installed():
        print("Installing dependencies from requirements.txt...")
        subprocess.check_call([VENV_PY, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([VENV_PY, "-m", "pip", "install", "-r", REQUIREMENTS])

    # A browser is only needed to run an actual audit, not to launch the apps.
    # Best-effort install of Playwright's Chromium; if it's unavailable (e.g.
    # unsupported OS), fall back to the system Chrome the apps use via
    # channel="chrome" and just warn — never block startup.
    if not _browser_available():
        print("Installing Playwright Chromium (best-effort)...")
        try:
            subprocess.check_call([VENV_PY, "-m", "playwright", "install", "chromium"])
        except subprocess.CalledProcessError:
            print(
                "  Note: could not install Playwright's Chromium on this system.\n"
                "  The apps will still start; audits require Google Chrome to be\n"
                "  installed (the apps launch it via channel=\"chrome\")."
            )

    # Re-exec under the venv's Python so sys.executable (used to spawn the
    # apps below) points at the venv interpreter.
    os.execv(VENV_PY, [VENV_PY, os.path.abspath(__file__), *sys.argv[1:]])


def main():
    print("Starting Script Auditor...")
    print("  V1 (Flask):     http://localhost:7070")
    print("  V2 (Streamlit): http://localhost:8501")
    print()
    print("Press Ctrl+C to stop both.\n")

    env = os.environ.copy()
    env["PATH"] = VENV_BIN + ":" + env["PATH"]

    flask_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=SCRIPT_DIR,
        env=env,
    )

    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
         "--server.port", "8501", "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=SCRIPT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def shutdown(signum, frame):
        print("\nShutting down...")
        flask_proc.terminate()
        streamlit_proc.terminate()
        flask_proc.wait()
        streamlit_proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while flask_proc.poll() is None and streamlit_proc.poll() is None:
        try:
            flask_proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    streamlit_proc.wait()


if __name__ == "__main__":
    if not _running_in_venv():
        ensure_venv()
    main()
