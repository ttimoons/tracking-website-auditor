"""
db.py — Database interface for Script Auditor using Turso (libsql).
Handles connection management, schema initialization, audit history CRUD,
and raw database table viewer operations.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

import certifi
from dotenv import load_dotenv

# Ensure macOS SSL certificate bundle is configured for aiohttp / python
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("script_auditor.db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def get_normalized_url(raw_url: str) -> str:
    """libsql-client over HTTPS requires https:// scheme instead of libsql://"""
    if not raw_url:
        return ""
    if raw_url.startswith("libsql://"):
        return raw_url.replace("libsql://", "https://", 1)
    return raw_url


def is_configured() -> bool:
    """Return True if Turso environment variables are set."""
    return bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def _get_client():
    """Create and return a libsql_client sync client instance, or None if unconfigured."""
    if not is_configured():
        return None
    try:
        import libsql_client
        url = get_normalized_url(TURSO_DATABASE_URL)
        return libsql_client.create_client_sync(url, auth_token=TURSO_AUTH_TOKEN)
    except Exception as e:
        logger.error(f"Failed to create Turso database client: {e}")
        return None


def init_db() -> bool:
    """Initialize database tables and indexes if they don't exist."""
    if not is_configured():
        logger.info("Turso DB not configured (missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN). History disabled.")
        return False

    client = _get_client()
    if not client:
        return False

    try:
        with client:
            client.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    gtm_detected INTEGER NOT NULL DEFAULT 0,
                    total_scripts INTEGER NOT NULL DEFAULT 0,
                    external_count INTEGER NOT NULL DEFAULT 0,
                    inline_count INTEGER NOT NULL DEFAULT 0,
                    via_gtm_count INTEGER NOT NULL DEFAULT 0,
                    blocked_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    details_json TEXT NOT NULL
                );
            """)
            client.execute("CREATE INDEX IF NOT EXISTS idx_audits_scanned_at ON audits(scanned_at DESC);")
            client.execute("CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url);")
        logger.info("Turso database initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Error initializing Turso database schema: {e}")
        return False


def save_audit(result: dict) -> int | None:
    """Save an audit result dict to Turso database.
    Returns the newly inserted audit ID, or None on failure.
    """
    client = _get_client()
    if not client:
        return None

    try:
        url = result.get("url", "")
        scanned_at = result.get("scanned_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        gtm_detected = 1 if result.get("gtm_detected") else 0
        error = result.get("error")

        scripts = result.get("scripts", [])
        total_scripts = len(scripts)
        external_count = sum(1 for s in scripts if s.get("type") == "external")
        inline_count = sum(1 for s in scripts if s.get("type") == "inline")
        via_gtm_count = sum(1 for s in scripts if s.get("via_gtm"))
        blocked_count = sum(1 for s in scripts if s.get("blocked"))

        details_json = json.dumps(result)

        with client:
            rs = client.execute(
                """
                INSERT INTO audits (
                    url, scanned_at, gtm_detected, total_scripts,
                    external_count, inline_count, via_gtm_count,
                    blocked_count, error, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id;
                """,
                [
                    url, scanned_at, gtm_detected, total_scripts,
                    external_count, inline_count, via_gtm_count,
                    blocked_count, error, details_json
                ]
            )
            inserted_id = rs.rows[0][0] if rs.rows else None
            logger.info(f"Saved audit for {url} to Turso (ID: {inserted_id})")
            return inserted_id
    except Exception as e:
        logger.error(f"Failed to save audit result to Turso DB: {e}")
        return None


def get_history(limit: int = 50, search: str = None) -> list[dict]:
    """Retrieve list of past audit summaries sorted by timestamp DESC.
    Does not load heavy details_json per row.
    """
    client = _get_client()
    if not client:
        return []

    try:
        query = """
            SELECT id, url, scanned_at, gtm_detected, total_scripts,
                   external_count, inline_count, via_gtm_count,
                   blocked_count, error
            FROM audits
        """
        args = []
        if search:
            query += " WHERE url LIKE ?"
            args.append(f"%{search.strip()}%")

        query += " ORDER BY scanned_at DESC, id DESC LIMIT ?"
        args.append(limit)

        with client:
            rs = client.execute(query, args)

        history = []
        for row in rs.rows:
            history.append({
                "id": row[0],
                "url": row[1],
                "scanned_at": row[2],
                "gtm_detected": bool(row[3]),
                "total_scripts": row[4],
                "external_count": row[5],
                "inline_count": row[6],
                "via_gtm_count": row[7],
                "blocked_count": row[8],
                "error": row[9],
            })
        return history
    except Exception as e:
        logger.error(f"Failed to fetch audit history from Turso DB: {e}")
        return []


def get_audit_by_id(audit_id: int) -> dict | None:
    """Retrieve full audit record (including result dict from details_json) by audit_id."""
    client = _get_client()
    if not client:
        return None

    try:
        with client:
            rs = client.execute(
                "SELECT id, url, scanned_at, details_json FROM audits WHERE id = ?",
                [audit_id]
            )
        if not rs.rows:
            return None

        row = rs.rows[0]
        details_json_str = row[3]
        result = json.loads(details_json_str)
        result["id"] = row[0]
        return result
    except Exception as e:
        logger.error(f"Failed to fetch audit ID {audit_id} from Turso DB: {e}")
        return None


def delete_audit(audit_id: int) -> bool:
    """Delete a specific audit record by ID."""
    client = _get_client()
    if not client:
        return False

    try:
        with client:
            client.execute("DELETE FROM audits WHERE id = ?", [audit_id])
        return True
    except Exception as e:
        logger.error(f"Failed to delete audit ID {audit_id} from Turso DB: {e}")
        return False


def clear_history() -> bool:
    """Delete all audit history records."""
    client = _get_client()
    if not client:
        return False

    try:
        with client:
            client.execute("DELETE FROM audits;")
        return True
    except Exception as e:
        logger.error(f"Failed to clear audit history from Turso DB: {e}")
        return False


def get_db_tables() -> list[dict]:
    """Return list of user tables in Turso DB with row counts."""
    client = _get_client()
    if not client:
        return []

    try:
        with client:
            rs = client.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_libsql_%';")
            tables = [row[0] for row in rs.rows]

            result = []
            for t in tables:
                rs_cnt = client.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = rs_cnt.rows[0][0] if rs_cnt.rows else 0
                result.append({"name": t, "row_count": cnt})
            return result
    except Exception as e:
        logger.error(f"Failed to fetch DB tables: {e}")
        return []


def get_table_data(table_name: str = "audits", page: int = 1, limit: int = 20, search: str = None) -> dict:
    """Retrieve raw table schema columns, paginated rows, and count for raw database viewer."""
    client = _get_client()
    if not client:
        return {"table": table_name, "columns": [], "rows": [], "total_rows": 0, "page": 1, "total_pages": 1}

    # Sanitize table name (only alphanumeric and underscore)
    clean_table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
    if not clean_table_name:
        clean_table_name = "audits"

    try:
        with client:
            rs_col = client.execute(f"SELECT * FROM {clean_table_name} LIMIT 1;")
            columns = list(rs_col.columns) if rs_col.columns else []

            where_clause = ""
            args = []
            if search and columns:
                conditions = [f"{col} LIKE ?" for col in columns]
                where_clause = " WHERE " + " OR ".join(conditions)
                search_param = f"%{search.strip()}%"
                args = [search_param] * len(columns)

            count_query = f"SELECT COUNT(*) FROM {clean_table_name}" + where_clause
            rs_count = client.execute(count_query, args)
            total_rows = rs_count.rows[0][0] if rs_count.rows else 0

            page = max(1, page)
            limit = max(1, min(limit, 100))
            total_pages = max(1, (total_rows + limit - 1) // limit)
            offset = (page - 1) * limit

            data_query = f"SELECT * FROM {clean_table_name}" + where_clause + f" ORDER BY 1 DESC LIMIT {limit} OFFSET {offset};"
            rs_data = client.execute(data_query, args)

            rows = []
            for row in rs_data.rows:
                row_dict = dict(zip(columns, row))
                rows.append(row_dict)

            return {
                "table": clean_table_name,
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows,
                "page": page,
                "total_pages": total_pages,
                "limit": limit
            }
    except Exception as e:
        logger.error(f"Failed to fetch table data for {clean_table_name}: {e}")
        return {"table": clean_table_name, "columns": [], "rows": [], "total_rows": 0, "page": 1, "total_pages": 1, "error": str(e)}


def get_history_stats() -> dict:
    """Retrieve aggregated audit statistics and global scripts log across history."""
    client = _get_client()
    if not client:
        return {
            "total_sessions": 0,
            "unique_urls": 0,
            "total_scripts": 0,
            "blocked_count": 0,
            "gtm_count": 0,
            "vendor_breakdown": {},
            "scripts_log": []
        }

    try:
        with client:
            rs_stats = client.execute("SELECT COUNT(*), COUNT(DISTINCT url), SUM(total_scripts), SUM(blocked_count), SUM(gtm_detected) FROM audits;")
            row = rs_stats.rows[0] if rs_stats.rows else [0, 0, 0, 0, 0]

            total_sessions = row[0] or 0
            unique_urls = row[1] or 0
            total_scripts = row[2] or 0
            blocked_count = row[3] or 0
            gtm_count = row[4] or 0

            rs_audits = client.execute("SELECT id, url, scanned_at, details_json FROM audits ORDER BY scanned_at DESC LIMIT 50;")
            
            vendor_counts = {}
            scripts_log = []

            for audit_row in rs_audits.rows:
                audit_id = audit_row[0]
                audit_url = audit_row[1]
                scanned_at = audit_row[2]
                try:
                    details = json.loads(audit_row[3])
                    for script in details.get("scripts", []):
                        vendor = script.get("vendor", "Unknown")
                        vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
                        scripts_log.append({
                            "audit_id": audit_id,
                            "scanned_at": scanned_at,
                            "audit_url": audit_url,
                            "url": script.get("url", ""),
                            "name": script.get("name", ""),
                            "vendor": vendor,
                            "type": script.get("type", ""),
                            "via_gtm": script.get("via_gtm", False),
                            "blocked": script.get("blocked", False),
                            "block_reason": script.get("block_reason")
                        })
                except Exception:
                    pass

            return {
                "total_sessions": total_sessions,
                "unique_urls": unique_urls,
                "total_scripts": total_scripts,
                "blocked_count": blocked_count,
                "gtm_count": gtm_count,
                "vendor_breakdown": vendor_counts,
                "scripts_log": scripts_log[:300]
            }
    except Exception as e:
        logger.error(f"Failed to fetch history stats: {e}")
        return {
            "total_sessions": 0,
            "unique_urls": 0,
            "total_scripts": 0,
            "blocked_count": 0,
            "gtm_count": 0,
            "vendor_breakdown": {},
            "scripts_log": []
        }
