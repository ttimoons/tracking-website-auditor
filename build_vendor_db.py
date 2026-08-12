#!/usr/bin/env python3
"""
build_vendor_db.py — Rebuild vendor_db.json domain-to-vendor database.
"""

import json
from pathlib import Path
from vendor_map import VENDOR_PATTERNS, _extract_domain

OUTPUT_PATH = Path(__file__).parent / "vendor_db.json"

DEFAULT_MAPPINGS = {
    "googletagmanager.com": "Google Tag Manager",
    "google-analytics.com": "Google Analytics",
    "googleadservices.com": "Google Ads",
    "doubleclick.net": "Google Ads (DoubleClick)",
    "facebook.net": "Facebook / Meta SDK",
    "facebook.com": "Facebook / Meta SDK",
    "hotjar.com": "Hotjar",
    "segment.com": "Segment",
    "segment.io": "Segment",
    "hubspot.com": "HubSpot",
    "hs-scripts.com": "HubSpot",
    "intercom.io": "Intercom",
    "intercomcdn.com": "Intercom",
    "licdn.com": "LinkedIn",
    "linkedin.com": "LinkedIn",
    "ads-twitter.com": "Twitter/X Ads Pixel",
    "twitter.com": "Twitter/X Platform",
    "clarity.ms": "Microsoft Clarity",
    "bing.com": "Bing Ads (UET)",
    "bat.bing.com": "Bing Ads (UET)",
    "heapanalytics.com": "Heap",
    "mxpnl.com": "Mixpanel",
    "mixpanel.com": "Mixpanel",
    "amplitude.com": "Amplitude",
    "fullstory.com": "FullStory",
    "pendo.io": "Pendo",
    "driftt.com": "Drift",
    "drift.com": "Drift",
    "zdassets.com": "Zendesk",
    "stripe.com": "Stripe",
    "sentry-cdn.com": "Sentry",
    "sentry.io": "Sentry",
    "browser-intake-datadoghq.com": "Datadog",
    "datadoghq.com": "Datadog",
    "nr-data.net": "New Relic",
    "newrelic.com": "New Relic",
    "posthog.com": "PostHog",
    "crisp.chat": "Crisp",
    "tiktok.com": "TikTok Pixel",
    "pinterest.com": "Pinterest Tag",
    "crazyegg.com": "Crazy Egg",
    "luckyorange.com": "Lucky Orange",
    "cookielaw.org": "OneTrust (CMP)",
    "cookiepro.com": "OneTrust (CMP)",
    "cookiebot.com": "Cookiebot (CMP)",
    "privacy-center.org": "Didomi (CMP)",
    "cookieyes.com": "CookieYes (CMP)",
    "cdn-cookieyes.com": "CookieYes (CMP)",
    "jquery.com": "jQuery (CDN)",
    "cloudflare.com": "Cloudflare CDNJS",
    "unpkg.com": "unpkg CDN",
    "jsdelivr.net": "jsDelivr CDN",
}


def main():
    db = dict(DEFAULT_MAPPINGS)
    for pattern, vendor in VENDOR_PATTERNS:
        domain = _extract_domain(f"https://{pattern}")
        if domain and domain not in db:
            db[domain] = vendor

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, sort_keys=True)

    print(f"Successfully generated {OUTPUT_PATH} with {len(db)} domain mappings.")


if __name__ == "__main__":
    main()
