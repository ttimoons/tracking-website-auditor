#!/usr/bin/env python3
"""
streamlit_app.py — Script Auditor V2 (Streamlit)

Run with: streamlit run streamlit_app.py --server.port 8501
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from audit_scripts import audit_url
from vendor_map import lookup_vendor

st.set_page_config(
    page_title="Script Auditor V2",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

VENDOR_ICONS = {
    "Google": "https://www.google.com/favicon.ico",
    "Google Ads": "https://www.google.com/favicon.ico",
    "Google Ads (DoubleClick)": "https://www.google.com/favicon.ico",
    "Google Tag Manager": "https://www.google.com/favicon.ico",
    "Google Analytics (UA)": "https://www.google.com/favicon.ico",
    "Google Analytics (Legacy)": "https://www.google.com/favicon.ico",
    "Google Analytics 4 (gtag)": "https://www.google.com/favicon.ico",
    "Google Optimize": "https://www.google.com/favicon.ico",
    "Google Hosted Libraries": "https://www.google.com/favicon.ico",
    "Facebook Pixel": "https://www.facebook.com/favicon.ico",
    "Facebook / Meta SDK": "https://www.facebook.com/favicon.ico",
    "Microsoft": "https://www.microsoft.com/favicon.ico",
    "Microsoft Clarity": "https://www.microsoft.com/favicon.ico",
    "Apple": "https://www.apple.com/favicon.ico",
    "Adobe": "https://www.adobe.com/favicon.ico",
    "Cloudflare": "https://www.cloudflare.com/favicon.ico",
    "Cloudflare CDNJS": "https://www.cloudflare.com/favicon.ico",
    "Amazon": "https://www.amazon.com/favicon.ico",
    "Shopify": "https://www.shopify.com/favicon.ico",
    "Stripe": "https://www.stripe.com/favicon.ico",
    "HubSpot": "https://www.hubspot.com/favicon.ico",
    "Salesforce": "https://www.salesforce.com/favicon.ico",
    "Zendesk": "https://www.zendesk.com/favicon.ico",
    "Intercom": "https://www.intercom.com/favicon.ico",
    "Drift": "https://www.drift.com/favicon.ico",
    "Hotjar": "https://www.hotjar.com/favicon.ico",
    "Segment": "https://www.segment.com/favicon.ico",
    "Mixpanel": "https://www.mixpanel.com/favicon.ico",
    "Amplitude": "https://www.amplitude.com/favicon.ico",
    "Heap": "https://www.heap.io/favicon.ico",
    "FullStory": "https://www.fullstory.com/favicon.ico",
    "Pendo": "https://www.pendo.io/favicon.ico",
    "PostHog": "https://www.posthog.com/favicon.ico",
    "Sentry": "https://www.sentry.io/favicon.ico",
    "Datadog": "https://www.datadog.com/favicon.ico",
    "New Relic": "https://www.newrelic.com/favicon.ico",
    "OneTrust": "https://www.onetrust.com/favicon.ico",
    "OneTrust (CMP)": "https://www.onetrust.com/favicon.ico",
    "Cookiebot": "https://www.cookiebot.com/favicon.ico",
    "Cookiebot (CMP)": "https://www.cookiebot.com/favicon.ico",
    "Didomi": "https://www.didomi.io/favicon.ico",
    "Didomi (CMP)": "https://www.didomi.io/favicon.ico",
    "Crisp": "https://www.crisp.chat/favicon.ico",
    "LinkedIn": "https://www.linkedin.com/favicon.ico",
    "LinkedIn Insight Tag": "https://www.linkedin.com/favicon.ico",
    "Twitter/X Ads Pixel": "https://www.twitter.com/favicon.ico",
    "Twitter/X Platform": "https://www.twitter.com/favicon.ico",
    "Pinterest Tag": "https://www.pinterest.com/favicon.ico",
    "TikTok Pixel": "https://www.tiktok.com/favicon.ico",
    "Criteo": "https://www.criteo.com/favicon.ico",
    "Outbrain": "https://www.outbrain.com/favicon.ico",
    "Quantcast": "https://www.quantcast.com/favicon.ico",
    "Taboola": "https://www.taboola.com/favicon.ico",
    "Yandex": "https://www.yandex.com/favicon.ico",
    "Baidu": "https://www.baidu.com/favicon.ico",
    "Alibaba": "https://www.alibaba.com/favicon.ico",
    "Fastly": "https://www.fastly.com/favicon.ico",
    "Akamai": "https://www.akamai.com/favicon.ico",
    "Vercel": "https://www.vercel.com/favicon.ico",
    "jQuery (CDN)": "https://www.jquery.com/favicon.ico",
    "unpkg CDN": "https://www.unpkg.com/favicon.ico",
    "jsDelivr CDN": "https://www.jsdelivr.com/favicon.ico",
}

CUSTOM_CSS = """
<style>
    .main .block-container { max-width: 1400px; padding-top: 2rem; }

    div[data-testid="stHeader"] {
        background: transparent;
    }

    .stApp {
        background: #0c0c0e;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        background-color: #161618 !important;
        border: 1px solid #38383a !important;
        color: #ffffff !important;
    }

    .stButton > button {
        background-color: #007aff !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover {
        background-color: #0056b3 !important;
    }

    .stButton > button:disabled {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
    }

    .stCheckbox > label {
        color: #c7c7cc !important;
        font-size: 0.8125rem !important;
    }

    .stCheckbox > label > div {
        border-color: #38383a !important;
    }

    .stCheckbox > label > div[data-baseweb="checkbox"][aria-checked="true"] {
        background-color: #007aff !important;
        border-color: #007aff !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #ffffff !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #a1a1a6 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
    }

    .vendor-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #38383a;
        background: #1c1c1f;
        color: #c7c7cc;
        font-size: 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        cursor: pointer;
        transition: all 0.15s;
    }

    .vendor-pill:hover {
        border-color: #007aff;
        background: #161618;
    }

    .vendor-pill.active {
        border-color: #007aff;
        background: rgba(0,122,255,0.12);
    }

    .vendor-pill img {
        width: 14px;
        height: 14px;
        border-radius: 2px;
    }

    .section-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #a1a1a6;
        margin-bottom: 8px;
    }

    .stDataFrame {
        border: 1px solid #38383a !important;
        border-radius: 8px !important;
    }

    .stDataFrame th {
        background-color: #161618 !important;
        color: #a1a1a6 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
    }

    .stDataFrame td {
        font-size: 0.8125rem !important;
        color: #ffffff !important;
    }

    .nav-link {
        position: fixed;
        top: 12px;
        right: 24px;
        z-index: 9999;
        padding: 6px 14px;
        border-radius: 6px;
        border: 1px solid #38383a;
        background: #161618;
        color: #a1a1a6;
        font-size: 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        text-decoration: none;
        transition: all 0.15s;
    }

    .nav-link:hover {
        border-color: #007aff;
        color: #ffffff;
    }
</style>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Script Auditor V2",
    "description": "Detect all JavaScript scripts loaded on a webpage, including GTM-injected ones. Identifies vendor, type, and blocked status.",
    "url": "http://localhost:8501",
    "applicationCategory": "DeveloperApplication",
    "operatingSystem": "Any",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
    },
    "author": {
        "@type": "Organization",
        "name": "Script Auditor"
    },
    "browserRequirements": "Requires JavaScript",
    "softwareVersion": "2.0.0",
    "featureList": [
        "JavaScript script detection",
        "Google Tag Manager script detection",
        "Vendor identification",
        "Cookie consent interaction",
        "Scroll-triggered script detection",
        "Blocked script detection"
    ]
}
</script>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(
    '<a href="http://localhost:7070" class="nav-link">← V1 (Flask)</a>',
    unsafe_allow_html=True,
)

st.title("Script Auditor")
st.caption("Detect all JS scripts loaded on a page, including GTM-injected ones")


def extract_domain(url):
    if url == "inline":
        return "inline"
    try:
        return urlparse(url).hostname or url
    except Exception:
        return url


def get_vendor_icon_html(vendor, size=14):
    icon = VENDOR_ICONS.get(vendor)
    if icon:
        return f'<img src="{icon}" width="{size}" height="{size}" style="border-radius:2px;vertical-align:middle" onerror="this.style.display=\'none\'" />'
    return ""


def run_audit(url, timeout, click_consent, scroll, scroll_count):
    from playwright.sync_api import sync_playwright

    interactions = {
        "click_consent": click_consent,
        "scroll": scroll,
        "scroll_count": scroll_count,
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            channel="chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            result = audit_url(url, browser, timeout * 1000, interactions)
        finally:
            browser.close()

    return result


# ── Init session state ──
if "scripts_data" not in st.session_state:
    st.session_state.scripts_data = []
if "last_url" not in st.session_state:
    st.session_state.last_url = ""
if "scanned_at" not in st.session_state:
    st.session_state.scanned_at = ""
if "gtm_detected" not in st.session_state:
    st.session_state.gtm_detected = False

# ── Input section ──
with st.container():
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        saved_url = st.session_state.last_url or ""
        url_input = st.text_input(
            "URL",
            value=saved_url,
            placeholder="https://example.com",
            label_visibility="collapsed",
        )
    with col2:
        timeout = st.selectbox(
            "Timeout",
            options=[20, 30, 45, 60, 90],
            index=1,
            label_visibility="collapsed",
        )
    with col3:
        audit_clicked = st.button("Audit", use_container_width=True, type="primary")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        click_consent = st.checkbox("Click cookie consent", value=True)
    with col_b:
        do_scroll = st.checkbox("Scroll page", value=True)
    with col_c:
        scroll_count = st.number_input("Scroll count", min_value=1, max_value=10, value=3)

# ── Run audit ──
if audit_clicked:
    if not url_input or not url_input.startswith(("http://", "https://")):
        st.error("Please enter a valid URL starting with http:// or https://")
    else:
        st.session_state.last_url = url_input
        with st.spinner("Launching browser and auditing page..."):
            try:
                result = run_audit(
                    url_input, timeout, click_consent, do_scroll, scroll_count
                )

                if result.get("error"):
                    st.error(result["error"])
                    st.session_state.scripts_data = []
                else:
                    st.session_state.scripts_data = result.get("scripts", [])
                    st.session_state.scanned_at = result.get("scanned_at", "")
                    st.session_state.gtm_detected = result.get("gtm_detected", False)
                    st.success(
                        f"Audit complete — found {len(result.get('scripts', []))} scripts"
                    )
            except Exception as e:
                st.error(f"Audit failed: {str(e)}")

# ── Results ──
scripts = st.session_state.scripts_data

if scripts:
    st.divider()

    # Metrics
    external = [s for s in scripts if s["type"] == "external"]
    inline = [s for s in scripts if s["type"] == "inline"]
    via_gtm = [s for s in scripts if s["via_gtm"]]
    blocked = [s for s in scripts if s["blocked"]]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Scripts", len(scripts))
    m2.metric("External", len(external))
    m3.metric("Inline", len(inline))
    m4.metric("Via GTM", len(via_gtm))
    m5.metric("Blocked", len(blocked))
    m6.metric(
        "GTM Status", "Detected" if st.session_state.gtm_detected else "Not detected"
    )

    st.divider()

    # Vendor breakdown
    st.markdown('<p class="section-label">Vendors detected</p>', unsafe_allow_html=True)

    vendor_counts = Counter(s["vendor"] for s in scripts)
    sorted_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)

    chips_html = ""
    for vendor, count in sorted_vendors:
        icon_html = get_vendor_icon_html(vendor)
        chips_html += f'<span class="vendor-pill">{icon_html}{vendor} <span style="opacity:0.6">({count})</span></span> '

    st.markdown(chips_html, unsafe_allow_html=True)

    st.divider()

    # ── Build DataFrame ──
    rows = []
    for s in scripts:
        domain = extract_domain(s["url"])
        icon_html = get_vendor_icon_html(s["vendor"])
        vendor_display = f"{icon_html} {s['vendor']}" if icon_html else s["vendor"]

        rows.append(
            {
                "Name": s.get("name", ""),
                "Vendor": s["vendor"],
                "Type": s["type"],
                "Via GTM": "Yes" if s["via_gtm"] else "No",
                "Blocked": "Yes" if s["blocked"] else "No",
                "Block Reason": s.get("block_reason", ""),
                "Domain": domain,
                "URL": s["url"],
            }
        )

    df = pd.DataFrame(rows)

    # Filters
    st.markdown('<p class="section-label">Filter scripts</p>', unsafe_allow_html=True)

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        type_filter = st.selectbox(
            "Type",
            options=["All", "External", "Inline"],
            label_visibility="collapsed",
        )
    with filter_col2:
        vendor_filter = st.selectbox(
            "Vendor",
            options=["All"] + [v for v, _ in sorted_vendors],
            label_visibility="collapsed",
        )

    filtered = df.copy()
    if type_filter != "All":
        filtered = filtered[filtered["Type"] == type_filter.lower()]
    if vendor_filter != "All":
        filtered = filtered[filtered["Vendor"] == vendor_filter]

    # Display table
    display_cols = ["Name", "Vendor", "Type", "Via GTM", "Blocked", "Domain", "URL"]
    if any(filtered["Blocked"] == "Yes"):
        display_cols.insert(5, "Block Reason")

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        height=500,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Vendor": st.column_config.TextColumn("Vendor", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Via GTM": st.column_config.TextColumn("Via GTM", width="small"),
            "Blocked": st.column_config.TextColumn("Blocked", width="small"),
            "Block Reason": st.column_config.TextColumn("Block Reason", width="medium"),
            "Domain": st.column_config.TextColumn("Domain", width="medium"),
            "URL": st.column_config.LinkColumn(
                "URL", display_text="url", width="large"
            ),
        },
    )

    st.divider()
    st.caption(f"Scanned at {st.session_state.scanned_at}")

    # Export
    st.download_button(
        label="Download JSON",
        data=json.dumps(scripts, indent=2),
        file_name=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )
