#!/usr/bin/env python3
"""
app.py — Flask web UI for the JS script auditor.
Run with: python3 app.py
Then open: http://localhost:7070
"""

import json
import logging
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request
from playwright.sync_api import sync_playwright

from audit_scripts import audit_url
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Initialize Turso DB tables on app start
db.init_db()

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

def run_audit_job(job_id: str, url: str, timeout_ms: int, interactions: dict = None):
    q = _jobs[job_id]
    logger.info("Job %s started: %s (timeout=%dms)", job_id, url, timeout_ms)
    try:
        _send(q, "status", message="Launching browser...")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, channel="chrome", args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                _send(q, "status", message=f"Connecting to {url} ...")
                if interactions and (interactions.get('click_consent') or interactions.get('scroll')):
                    _send(q, "status", message="Performing interactions...")
                result = audit_url(url, browser, timeout_ms, interactions)
            finally:
                browser.close()

        if result.get("error"):
            logger.warning("Job %s audit error: %s", job_id, result["error"])
            _send(q, "error", message=result["error"])
        else:
            # Persist successful audit to Turso DB
            audit_id = db.save_audit(result)
            if audit_id:
                result["id"] = audit_id

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
        url = f"https://{url}"

    timeout_sec = int(body.get("timeout", 30))
    timeout_ms = max(5, min(timeout_sec, 120)) * 1000

    interactions = {
        'click_consent': body.get('click_consent', True),
        'scroll': body.get('scroll', True),
        'scroll_count': int(body.get('scroll_count', 3)),
    }

    job_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    with _jobs_lock:
        _jobs[job_id] = q

    t = threading.Thread(target=run_audit_job, args=(job_id, url, timeout_ms, interactions), daemon=True)
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
# History API Routes
# ---------------------------------------------------------------------------

@app.route("/api/history", methods=["GET"])
def get_history_list():
    search = request.args.get("q")
    limit = request.args.get("limit", 50, type=int)
    history = db.get_history(limit=limit, search=search)
    return jsonify({"history": history, "db_configured": db.is_configured()})


@app.route("/api/history/<int:audit_id>", methods=["GET"])
def get_history_detail(audit_id: int):
    audit = db.get_audit_by_id(audit_id)
    if not audit:
        return jsonify({"error": "Audit record not found"}), 404
    return jsonify(audit)


@app.route("/api/history/<int:audit_id>", methods=["DELETE"])
def delete_history_item(audit_id: int):
    success = db.delete_audit(audit_id)
    return jsonify({"success": success})


@app.route("/api/history/clear", methods=["POST", "DELETE"])
def clear_history():
    success = db.clear_history()
    return jsonify({"success": success})


@app.route("/api/history/stats", methods=["GET"])
def get_history_stats_api():
    stats = db.get_history_stats()
    return jsonify(stats)


@app.route("/api/db/tables", methods=["GET"])
def get_db_tables_api():
    tables = db.get_db_tables()
    return jsonify({"tables": tables})


@app.route("/api/db/table/<table_name>", methods=["GET"])
def get_db_table_data_api(table_name: str):
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("q")
    data = db.get_table_data(table_name, page=page, limit=limit, search=search)
    return jsonify(data)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting server at http://127.0.0.1:7070")
    app.run(debug=False, threaded=True, port=7070)

