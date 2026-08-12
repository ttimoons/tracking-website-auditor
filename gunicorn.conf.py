# Gunicorn configuration for script-auditor
# SSE requires long-lived connections → use sync workers with long timeout

import os

port = os.environ.get("PORT", "7070")
bind = f"0.0.0.0:{port}"
workers = 1          # must be 1 — job queue is in-process memory, not shared across workers
threads = 8          # handle concurrent audits + SSE streams within the single worker
timeout = 180        # seconds — must exceed max audit timeout (120s) + buffer
keepalive = 5
worker_class = "sync"

# Logging (local dev: stderr; VPS: use full paths)
accesslog = "-"
errorlog  = "-"
loglevel  = "info"
