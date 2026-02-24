#!/usr/bin/env python3
"""
app.py — Flask web UI for the JS script auditor.
Run with: python3 app.py
Then open: http://localhost:5000
"""

import json
import logging
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request
from playwright.sync_api import sync_playwright

from audit_scripts import audit_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# job_id -> queue.Queue of SSE event dicts
_jobs: dict[str, queue.Queue] = {}
_jobs_lock = threading.Lock()


def _send(q: queue.Queue, event_type: str, **kwargs):
    q.put({"type": event_type, **kwargs})


# ---------------------------------------------------------------------------
# Background audit worker
# Each thread owns its own Playwright instance — sync_playwright is not
# thread-safe and cannot be shared across threads.
# ---------------------------------------------------------------------------

def run_audit_job(job_id: str, url: str, timeout_ms: int):
    q = _jobs[job_id]
    logger.info("Job %s started: %s (timeout=%dms)", job_id, url, timeout_ms)
    try:
        _send(q, "status", message="Launching browser...")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                _send(q, "status", message=f"Connecting to {url} ...")
                result = audit_url(url, browser, timeout_ms)
            finally:
                browser.close()

        if result.get("error"):
            logger.warning("Job %s audit error: %s", job_id, result["error"])
            _send(q, "error", message=result["error"])
        else:
            _send(q, "status", message="Processing results...")
            _send(q, "result", data=result)
            logger.info("Job %s completed: %d scripts found", job_id, len(result.get("scripts", [])))
    except Exception as e:
        logger.exception("Job %s raised an unexpected exception", job_id)
        _send(q, "error", message=str(e))
    finally:
        _send(q, "done")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/audit", methods=["POST"])
def start_audit():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "URL must start with http:// or https://"}), 400

    timeout_sec = int(body.get("timeout", 30))
    timeout_ms = max(5, min(timeout_sec, 120)) * 1000

    job_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    with _jobs_lock:
        _jobs[job_id] = q

    t = threading.Thread(target=run_audit_job, args=(job_id, url, timeout_ms), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/stream/<job_id>")
def stream(job_id: str):
    with _jobs_lock:
        q = _jobs.get(job_id)
    if q is None:
        return Response("Job not found", status=404)

    def generate():
        while True:
            try:
                event = q.get(timeout=120)
            except queue.Empty:
                yield "data: {\"type\": \"error\", \"message\": \"Timeout waiting for results\"}\n\n"
                break

            payload = json.dumps(event)
            yield f"data: {payload}\n\n"

            if event["type"] in ("done", "error"):
                # Clean up job
                with _jobs_lock:
                    _jobs.pop(job_id, None)
                break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting server at http://127.0.0.1:7070")
    app.run(debug=False, threaded=True, port=7070)
