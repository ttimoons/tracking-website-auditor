#!/usr/bin/env python3
"""
audit_scripts.py — Detect all JavaScript scripts loaded on a webpage,
including those injected by Google Tag Manager.

Usage:
  python audit_scripts.py <url>
  python audit_scripts.py --file urls.txt
  python audit_scripts.py <url> --output my-audit.json --verbose
  python audit_scripts.py <url> --no-headless --timeout 45
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, sync_playwright

from vendor_map import infer_vendor_from_inline, lookup_vendor

# URLs to ignore (GTM internal / debug endpoints)
_FILTERED_URL_FRAGMENTS = [
    "googletagmanager.com/gtm/init",
    "googletagmanager.com/gtm/preview",
    "googletagmanager.com/debug",
]

_CONSENT_SELECTORS = [
    "[id*='accept'][id*='cookie']",
    "[id*='cookie'][id*='accept']",
    "[class*='accept'][class*='cookie']",
    "[class*='cookie'][class*='accept']",
    "[id*='accept-cookies']",
    "[class*='accept-cookies']",
    "button[id*='accept']",
    "button[class*='accept']",
    "a[id*='accept']",
    "a[class*='accept']",
    "[id*='agree']",
    "[class*='agree']",
    "button[id*='consent']",
    "button[class*='consent']",
    "[id*='cc-accept']",
    "[class*='cc-accept']",
    "[id*='gdpr-accept']",
    "[class*='gdpr-accept']",
    "[aria-label*='accept']",
    "[aria-label*='Accept']",
    "[aria-label*='agree']",
    "[aria-label*='Agree']",
    "[aria-label*='consent']",
    "[aria-label*='Consent']",
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
    "button:has-text('Accept all')",
    "button:has-text('I accept')",
    "button:has-text('I Accept')",
    "button:has-text('Agree')",
    "button:has-text('I agree')",
    "button:has-text('I Agree')",
    "button:has-text('OK')",
    "button:has-text('Okay')",
    "button:has-text('Continue')",
    "a:has-text('Accept')",
    "a:has-text('Agree')",
    "[data-testid*='accept']",
    "[data-testid*='consent']",
    "[data-testid*='agree']",
    "#onetrust-accept-btn-handler",
    ".accept-cookies",
    ".cc-accept",
    ".cc-dismiss",
    "#cookie-accept",
    "#cookies-accept",
    "#accept-cookies",
    "#acceptCookies",
    "#accept-cookie",
    ".cookie-consent-accept",
    "#consent-accept",
    ".consent-accept",
]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def infer_name(url: str) -> str:
    """Extract a human-readable script name from a URL."""
    if url == "inline":
        return "inline"
    try:
        path = urlparse(url).path.rstrip("/")
        filename = path.split("/")[-1] if "/" in path else path
        # Strip query params that crept into the filename
        filename = filename.split("?")[0]
        if filename:
            return filename
        # Fallback: use hostname
        return urlparse(url).hostname or url
    except Exception:
        return url


def is_gtm_request(url: str) -> bool:
    """Return True if this URL is the GTM container loader.
    Covers both standard and server-side GTM (custom domain proxies).
    """
    lower = url.lower()
    # Standard GTM
    if "googletagmanager.com/gtm.js" in lower:
        return True
    if "googletagmanager.com/gtag/js" in lower:
        return True
    # Server-side GTM: custom domain serving /gtm.js?id=GTM-XXXX or /gtag/js?id=...
    if "/gtm.js" in lower and "id=gtm-" in lower:
        return True
    if "/gtag/js" in lower and ("id=g-" in lower or "id=gtm-" in lower):
        return True
    return False


def is_filtered_url(url: str) -> bool:
    """Return True if this URL should be ignored (GTM internal endpoints)."""
    lower = url.lower()
    return any(fragment in lower for fragment in _FILTERED_URL_FRAGMENTS)


def classify_error(raw: str) -> str:
    """Turn a raw Playwright/network error string into a short human-readable note."""
    s = raw.lower()
    if "net::err_blocked_by_client" in s or "adblock" in s:
        return "Blocked by ad blocker / browser extension"
    if "net::err_connection_refused" in s:
        return "Connection refused"
    if "net::err_connection_timed_out" in s or "timeout" in s:
        return "Connection timed out"
    if "net::err_name_not_resolved" in s or "dns" in s:
        return "DNS resolution failed (domain not found)"
    if "net::err_ssl" in s or "ssl" in s or "certificate" in s:
        return "SSL / certificate error"
    if "net::err_aborted" in s:
        return "Request aborted"
    if "net::err_failed" in s:
        return "Network request failed"
    if "403" in s or "forbidden" in s:
        return "403 Forbidden"
    if "401" in s or "unauthorized" in s:
        return "401 Unauthorized"
    if "404" in s or "not found" in s:
        return "404 Not Found"
    if "cors" in s or "cross-origin" in s:
        return "Blocked by CORS policy"
    if "blocked" in s:
        return "Request blocked"
    return f"Request failed: {raw[:120]}"


def classify_page_error(raw: str) -> str:
    """Turn a page.goto() exception into a readable message."""
    s = raw.lower()
    if "timeout" in s:
        return "Page load timed out — site may be slow or blocking automated browsers"
    if "net::err_name_not_resolved" in s:
        return "Domain not found — check the URL"
    if "net::err_connection_refused" in s:
        return "Connection refused — site may be down"
    if "net::err_connection_timed_out" in s:
        return "Connection timed out — site may be slow or unreachable"
    if "net::err_ssl" in s or "certificate" in s:
        return "SSL certificate error"
    if "net::err_aborted" in s:
        return "Page load aborted — site may be blocking automated access"
    if "net::err_failed" in s:
        return "Network request failed — site may be blocking automated browsers"
    if "blocked" in s:
        return "Page load blocked — site is rejecting automated browsers"
    return raw


def try_click_consent_banner(page: Page) -> bool:
    """Attempt to click a cookie consent/cookie banner accept button.
    Returns True if a button was clicked.
    """
    for selector in _CONSENT_SELECTORS:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click(timeout=1000)
                page.wait_for_timeout(500)
                return True
        except Exception:
            continue
    return False


def perform_scroll(page: Page, scroll_count: int =3, scroll_delay: int = 800) -> None:
    """Scroll the page to trigger lazy-loaded scripts."""
    for i in range(scroll_count):
        try:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i +1) / scroll_count})")
            page.wait_for_timeout(scroll_delay)
        except Exception:
            break


def perform_interactions(
    page: Page,
    interactions: dict,
    captured_requests: list,
    failed_requests: dict,
    gtm_detected: bool
) -> bool:
    """Perform user interactions on the page.
    interactions: dict with keys 'click_consent', 'scroll', 'scroll_count'
    Returns True if any interaction triggered new scripts.
    """
    initial_count = len(captured_requests)
    did_interact = False

    if interactions.get('click_consent', True):
        if try_click_consent_banner(page):
            did_interact = True
            page.wait_for_timeout(1000)

    if interactions.get('scroll', True):
        scroll_count = interactions.get('scroll_count', 3)
        perform_scroll(page, scroll_count)
        did_interact = True

    return did_interact and len(captured_requests) > initial_count


def build_script_record(
    url: str, name: str, vendor: str, via_gtm: bool, script_type: str,
    blocked: bool = False, block_reason: str = None
) -> dict:
    record = {
        "url": url,
        "name": name,
        "vendor": vendor,
        "via_gtm": via_gtm,
        "type": script_type,
        "blocked": blocked,
    }
    if block_reason:
        record["block_reason"] = block_reason
    return record


# ---------------------------------------------------------------------------
# Page inspection
# ---------------------------------------------------------------------------

def extract_inline_scripts(page: Page) -> list:
    """Return records for all non-empty inline <script> tags."""
    try:
        contents = page.eval_on_selector_all(
            "script:not([src])",
            "els => els.map(el => el.textContent || '')"
        )
    except Exception:
        return []

    records = []
    for content in contents:
        content = content.strip()
        if not content:
            continue
        vendor = infer_vendor_from_inline(content)
        records.append(build_script_record("inline", "inline", vendor, False, "inline"))
    return records


def get_dom_script_urls(page: Page) -> set:
    """Return the set of absolute src URLs from <script src> elements in the DOM."""
    try:
        urls = page.eval_on_selector_all(
            "script[src]",
            "els => els.map(el => el.src)"
        )
        return set(u for u in urls if u)
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Core audit
# ---------------------------------------------------------------------------

def audit_url(
    url: str,
    browser: Browser,
    timeout_ms: int,
    interactions: dict = None
) -> dict:
    """Audit a single URL and return a result dict.
    interactions: dict with 'click_consent', 'scroll', 'scroll_count' keys
    """
    if interactions is None:
        interactions = {'click_consent': True, 'scroll': True, 'scroll_count': 3}
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()

    captured_requests: list = []
    failed_requests: dict = {}  # url -> block_reason string
    gtm_detected = False

    def handle_request(request):
        nonlocal gtm_detected
        if request.resource_type == "script":
            req_url = request.url
            if is_filtered_url(req_url):
                return
            captured_requests.append(req_url)
            if is_gtm_request(req_url):
                gtm_detected = True

    def handle_request_failed(request):
        if request.resource_type == "script":
            req_url = request.url
            if is_filtered_url(req_url):
                return
            reason = classify_error(request.failure or "")
            failed_requests[req_url] = reason
            # Still track it so it appears in results
            if req_url not in captured_requests:
                captured_requests.append(req_url)

    def handle_response(response):
        if response.request.resource_type == "script":
            status = response.status
            if status in (401, 403, 404, 429) or status >= 500:
                req_url = response.url
                if not is_filtered_url(req_url):
                    reason = classify_error(str(status))
                    failed_requests[req_url] = reason

    page.on("request", handle_request)
    page.on("requestfailed", handle_request_failed)
    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    except Exception as e:
        context.close()
        return {
            "url": url,
            "scanned_at": _now_iso(),
            "gtm_detected": False,
            "error": classify_page_error(str(e)),
            "scripts": [],
        }

    # Perform user interactions to trigger blocked scripts
    perform_interactions(page, interactions, captured_requests, failed_requests, gtm_detected)

    # Extra buffer for late-firing GTM tags
    try:
        page.wait_for_timeout(2000)
    except Exception:
        pass

    # Snapshot DOM scripts (present in initial HTML or injected synchronously)
    dom_script_urls = get_dom_script_urls(page)

    # Inline scripts
    inline_records = extract_inline_scripts(page)

    # External scripts present in the DOM
    dom_external_records = []
    for script_url in dom_script_urls:
        name = infer_name(script_url)
        vendor = lookup_vendor(script_url)
        blocked = script_url in failed_requests
        dom_external_records.append(
            build_script_record(script_url, name, vendor, False, "external",
                                blocked=blocked,
                                block_reason=failed_requests.get(script_url))
        )

    # Dynamic scripts = network-captured but not in the DOM snapshot
    dynamic_records = []
    for script_url in captured_requests:
        if script_url not in dom_script_urls:
            name = infer_name(script_url)
            vendor = lookup_vendor(script_url)
            blocked = script_url in failed_requests
            dynamic_records.append(
                build_script_record(script_url, name, vendor, gtm_detected, "external",
                                    blocked=blocked,
                                    block_reason=failed_requests.get(script_url))
            )

    context.close()

    # Combine and deduplicate by (url, type)
    all_scripts = inline_records + dom_external_records + dynamic_records
    seen = set()
    deduped = []
    for s in all_scripts:
        key = (s["url"], s["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return {
        "url": url,
        "scanned_at": _now_iso(),
        "gtm_detected": gtm_detected,
        "error": None,
        "scripts": deduped,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Output / display
# ---------------------------------------------------------------------------

def print_result(result: dict, verbose: bool, index: int = None, total: int = None) -> None:
    prefix = f"[{index}/{total}] " if index is not None else ""
    print(f"\n{prefix}Auditing: {result['url']}")

    if result.get("error"):
        print(f"  ERROR: {result['error']}")
        return

    scripts = result["scripts"]
    inline_count = sum(1 for s in scripts if s["type"] == "inline")
    external_count = sum(1 for s in scripts if s["type"] == "external")
    via_gtm_count = sum(1 for s in scripts if s["via_gtm"])

    print(f"  Found {len(scripts)} scripts ({inline_count} inline, {external_count} external)")
    print(f"  GTM detected: {'YES' if result['gtm_detected'] else 'NO'}")
    if result["gtm_detected"]:
        print(f"  Scripts injected via GTM: {via_gtm_count}")

    vendor_counts = Counter(s["vendor"] for s in scripts)
    if vendor_counts:
        print("  Vendor breakdown:")
        for vendor, count in vendor_counts.most_common():
            print(f"    {vendor:<35} {count}")

    if verbose and scripts:
        print()
        header = f"  {'URL':<55} {'Name':<20} {'Vendor':<30} {'GTM':<5} {'Type'}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for s in scripts:
            short_url = s["url"]
            if len(short_url) > 53:
                short_url = short_url[:50] + "..."
            gtm_flag = "Yes" if s["via_gtm"] else "No"
            print(
                f"  {short_url:<55} {s['name']:<20} {s['vendor']:<30} {gtm_flag:<5} {s['type']}"
            )


def save_results(results, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect all JS scripts on a webpage, including GTM-injected ones.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Single URL to audit (e.g. https://example.com)",
    )
    parser.add_argument(
        "--file", "-f",
        metavar="FILE",
        help="Path to a .txt file with one URL per line",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output JSON file path (default: output/audit_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Timeout per URL in seconds (default: 30)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show the browser window (useful for debugging)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print a table of all detected scripts per URL",
    )
    parser.add_argument(
        "--no-click-consent",
        action="store_true",
        help="Disable automatic clicking of cookie consent banners",
    )
    parser.add_argument(
        "--no-scroll",
        action="store_true",
        help="Disable automatic page scrolling to trigger lazy-loaded scripts",
    )
    parser.add_argument(
        "--scroll-count",
        type=int,
        default=3,
        metavar="N",
        help="Number of scroll steps (default: 3)",
    )
    return parser.parse_args()


def load_urls(args: argparse.Namespace) -> list:
    if args.url and args.file:
        sys.exit("Error: provide either a URL or --file, not both.")
    if not args.url and not args.file:
        sys.exit("Error: provide a URL or --file <path>.")

    if args.url:
        urls = [args.url.strip()]
    else:
        file_path = Path(args.file)
        if not file_path.exists():
            sys.exit(f"Error: file not found: {args.file}")
        lines = file_path.read_text(encoding="utf-8").splitlines()
        urls = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        if not urls:
            sys.exit(f"Error: no URLs found in {args.file}")

    validated = []
    for u in urls:
        if not u.startswith(("http://", "https://")):
            print(f"Warning: skipping invalid URL (no http/https): {u}", file=sys.stderr)
            continue
        validated.append(u)

    if not validated:
        sys.exit("Error: no valid URLs to audit.")
    return validated


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_audit(urls: list, args: argparse.Namespace) -> None:
    timeout_ms = args.timeout * 1000
    headless = not args.no_headless
    total = len(urls)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or f"output/audit_{timestamp}.json"

    interactions = {
        'click_consent': not args.no_click_consent,
        'scroll': not args.no_scroll,
        'scroll_count': args.scroll_count,
    }

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, channel="chrome")
        try:
            for i, url in enumerate(urls, start=1):
                result = audit_url(url, browser, timeout_ms, interactions)
                results.append(result)
                print_result(result, args.verbose, index=i, total=total)
        except KeyboardInterrupt:
            print("\nInterrupted. Saving partial results...")
        finally:
            browser.close()

    output_data = results[0] if len(results) == 1 else results
    save_results(output_data, output_path)


def main() -> None:
    args = parse_args()
    urls = load_urls(args)
    run_audit(urls, args)


if __name__ == "__main__":
    main()
