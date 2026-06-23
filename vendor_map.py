#!/usr/bin/env python3
"""
vendor_map.py — Map script URLs to vendor names using pattern matching
and DuckDuckGo Tracker Radar data.

Data sources:
- Bundled vendor_db.json (from DuckDuckGo Tracker Radar)
- Fallback pattern matching for common scripts
"""

import json
from pathlib import Path
from urllib.parse import urlparse

_VENDOR_DB_PATH = Path(__file__).parent / "vendor_db.json"
_vendor_db: dict = {}

VENDOR_PATTERNS = [
    ("googletagmanager.com/gtm.js", "Google Tag Manager"),
    ("googletagmanager.com/gtag/js", "Google Tag Manager"),
    ("google-analytics.com/analytics.js", "Google Analytics (UA)"),
    ("google-analytics.com/ga.js", "Google Analytics (Legacy)"),
    ("googletagmanager.com/gtag", "Google Analytics 4 (gtag)"),
    ("googleadservices.com/pagead", "Google Ads"),
    ("doubleclick.net", "Google Ads (DoubleClick)"),
    ("google.com/pagead", "Google Ads"),
    ("google-analytics.com/cx/api.js", "Google Optimize"),
    ("connect.facebook.net/en_us/fbevents", "Facebook Pixel"),
    ("connect.facebook.net", "Facebook / Meta SDK"),
    ("static.hotjar.com", "Hotjar"),
    ("script.hotjar.com", "Hotjar"),
    ("cdn.segment.com", "Segment"),
    ("segment.io", "Segment"),
    ("js.hs-scripts.com", "HubSpot"),
    ("js.hubspot.com", "HubSpot"),
    ("hubspot.com", "HubSpot"),
    ("widget.intercom.io", "Intercom"),
    ("js.intercomcdn.com", "Intercom"),
    ("intercom.io", "Intercom"),
    ("snap.licdn.com", "LinkedIn Insight Tag"),
    ("platform.linkedin.com", "LinkedIn"),
    ("static.ads-twitter.com", "Twitter/X Ads Pixel"),
    ("platform.twitter.com", "Twitter/X Platform"),
    ("clarity.ms", "Microsoft Clarity"),
    ("cdn.heapanalytics.com", "Heap"),
    ("heapanalytics.com", "Heap"),
    ("cdn.mxpnl.com", "Mixpanel"),
    ("cdn4.mxpnl.com", "Mixpanel"),
    ("mixpanel.com", "Mixpanel"),
    ("cdn.amplitude.com", "Amplitude"),
    ("amplitude.com", "Amplitude"),
    ("fullstory.com/s/fs.js", "FullStory"),
    ("rs.fullstory.com", "FullStory"),
    ("edge.fullstory.com", "FullStory"),
    ("cdn.pendo.io", "Pendo"),
    ("app.pendo.io", "Pendo"),
    ("js.driftt.com", "Drift"),
    ("cdn.drift.com", "Drift"),
    ("static.zdassets.com", "Zendesk"),
    ("ekr.zdassets.com", "Zendesk"),
    ("js.stripe.com", "Stripe"),
    ("browser.sentry-cdn.com", "Sentry"),
    ("js.sentry-cdn.com", "Sentry"),
    ("sentry.io", "Sentry"),
    ("browser-intake-datadoghq.com", "Datadog"),
    ("rum.browser-intake-datadoghq.com", "Datadog"),
    ("datadoghq.com", "Datadog"),
    ("js-agent.newrelic.com", "New Relic"),
    ("bam.nr-data.net", "New Relic"),
    ("cdn.posthog.com", "PostHog"),
    ("us.i.posthog.com", "PostHog"),
    ("eu.i.posthog.com", "PostHog"),
    ("app.posthog.com", "PostHog"),
    ("posthog.com", "PostHog"),
    ("client.crisp.chat", "Crisp"),
    ("analytics.tiktok.com", "TikTok Pixel"),
    ("s.pinimg.com", "Pinterest Tag"),
    ("ct.pinterest.com", "Pinterest Tag"),
    ("script.crazyegg.com", "Crazy Egg"),
    ("luckyorange.com", "Lucky Orange"),
    ("cdn.cookielaw.org", "OneTrust (CMP)"),
    ("optanon.blob.core.windows.net", "OneTrust (CMP)"),
    ("cookie-cdn.cookiepro.com", "OneTrust (CMP)"),
    ("consent.cookiebot.com", "Cookiebot (CMP)"),
    ("sdk.privacy-center.org", "Didomi (CMP)"),
    ("code.jquery.com", "jQuery (CDN)"),
    ("ajax.googleapis.com/ajax/libs", "Google Hosted Libraries"),
    ("cdnjs.cloudflare.com", "Cloudflare CDNJS"),
    ("unpkg.com", "unpkg CDN"),
    ("jsdelivr.net", "jsDelivr CDN"),
]

_INLINE_FINGERPRINTS = [
    ("gtag(", "Google Analytics 4 (gtag)"),
    ("GoogleAnalyticsObject", "Google Analytics (UA)"),
    ("fbq(", "Facebook Pixel"),
    ("_fbq", "Facebook Pixel"),
    ("hj(", "Hotjar"),
    ("_hsq", "HubSpot"),
    ("intercomSettings", "Intercom"),
    ("Intercom(", "Intercom"),
    ("analytics.load(", "Segment"),
    ("amplitude.getInstance", "Amplitude"),
    ("mixpanel.init", "Mixpanel"),
    ("heap.load(", "Heap"),
    ("pendo.initialize", "Pendo"),
    ("drift.load(", "Drift"),
    ("FS.identify", "FullStory"),
    ("clarity(", "Microsoft Clarity"),
    ("lintrk(", "LinkedIn Insight Tag"),
    ("twq(", "Twitter/X Ads Pixel"),
    ("posthog.init(", "PostHog"),
    ("ttq.load(", "TikTok Pixel"),
    ("pintrk(", "Pinterest Tag"),
    ("dataLayer", "Google Tag Manager"),
]


def _load_vendor_db() -> dict:
    """Load the bundled vendor database."""
    global _vendor_db
    if _vendor_db:
        return _vendor_db
    try:
        if _VENDOR_DB_PATH.exists():
            with open(_VENDOR_DB_PATH) as f:
                _vendor_db = json.load(f)
    except Exception:
        pass
    return _vendor_db


def _extract_domain(url: str) -> str:
    """Extract registrable domain from URL."""
    if url == "inline":
        return ""
    try:
        host = urlparse(url).hostname
        if not host:
            return ""
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:]).lower()
        return host.lower()
    except Exception:
        return ""


def lookup_vendor(url: str) -> str:
    """Return the vendor name for a script URL, or 'Unknown'."""
    lowered = url.lower()

    if ("/gtm.js" in lowered and "id=gtm-" in lowered) or (
        "/gtag/js" in lowered and ("id=g-" in lowered or "id=gtm-" in lowered)
    ):
        return "Google Tag Manager"

    db = _load_vendor_db()
    domain = _extract_domain(url)
    if domain and domain in db:
        return db[domain]

    host_parts = domain.split(".")
    if len(host_parts) > 2:
        parent_domain = ".".join(host_parts[-2:])
        if parent_domain in db:
            return db[parent_domain]

    for pattern, vendor in VENDOR_PATTERNS:
        if pattern.lower() in lowered:
            return vendor

    return "Unknown"


def infer_vendor_from_inline(content: str) -> str:
    """Best-effort vendor detection from inline script content."""
    for fingerprint, vendor in _INLINE_FINGERPRINTS:
        if fingerprint in content:
            return vendor
    return "Unknown"