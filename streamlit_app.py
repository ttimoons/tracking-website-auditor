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
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        /* Brand palette */
        --slate:    #0C447C;
        --teal:     #1D9E75;
        --graphite: #5F5E5A;
        --sand:     #F1EFE8;
        --coral:    #D85A30;
        --amber:    #BA7517;
        --paper:    #F1EFE8;
        --ink:      #2C2C2A;

        /* Semantic tokens */
        --primary:       var(--slate);
        --primary-hover: #0A3866;
        --bg-dark:       #E8E4DC;
        --bg-card:       var(--paper);
        --field:         #FBFAF6;
        --text-main:     var(--ink);
        --text-muted:    var(--graphite);
        --border:        rgba(44, 44, 42, 0.16);
        --border-faint:  rgba(44, 44, 42, 0.08);
        --accent:        var(--teal);
        --error:         var(--coral);

        --font-display: 'Space Grotesk', system-ui, sans-serif;
        --font-mono:    'JetBrains Mono', ui-monospace, monospace;
    }

    .main .block-container { max-width: 1400px; padding-top: 2rem; }

    div[data-testid="stHeader"] {
        background: transparent;
    }

    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-main);
        /* faint engineering-paper grid */
        background-image:
            linear-gradient(rgba(44, 44, 42, 0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(44, 44, 42, 0.035) 1px, transparent 1px);
        background-size: 28px 28px;
    }

    /* Structural type → Space Grotesk, tight tracking */
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
        font-family: var(--font-display);
    }

    h1, h2, h3, .stApp h1, .stApp h2, .stApp h3 {
        font-family: var(--font-display) !important;
        font-weight: 700 !important;
        letter-spacing: -0.035em !important;
        color: var(--text-main) !important;
    }

    /* App title + caption */
    .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stCaptionContainer"] p {
        font-family: var(--font-mono) !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--text-muted) !important;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput > div > div > input {
        background-color: var(--field) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0.6rem !important;
        color: var(--text-main) !important;
        font-family: var(--font-mono) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(12, 68, 124, 0.12) !important;
    }

    .stTextInput input::placeholder { color: var(--text-muted) !important; }

    .stButton > button {
        background-color: var(--primary) !important;
        color: var(--sand) !important;
        border: none !important;
        border-radius: 0.6rem !important;
        font-family: var(--font-display) !important;
        font-weight: 700 !important;
        transition: background 0.15s ease, transform 0.15s ease !important;
    }

    .stButton > button:hover {
        background-color: var(--primary-hover) !important;
        transform: translateY(-1px);
    }

    .stButton > button:disabled {
        opacity: 0.45 !important;
        cursor: default !important;
        transform: none !important;
    }

    .stCheckbox > label {
        color: var(--text-main) !important;
        font-size: 0.8125rem !important;
    }

    .stCheckbox > label > div {
        border-color: var(--border) !important;
    }

    .stCheckbox > label > div[data-baseweb="checkbox"][aria-checked="true"] {
        background-color: var(--primary) !important;
        border-color: var(--primary) !important;
    }

    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        box-shadow: 0 1px 0 rgba(44, 44, 42, 0.04);
        padding: 12px 16px;
    }

    div[data-testid="stMetricValue"] {
        font-family: var(--font-display) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.04em !important;
        color: var(--text-main) !important;
    }

    div[data-testid="stMetricLabel"] {
        font-family: var(--font-mono) !important;
        color: var(--text-muted) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }

    /* Hairline dividers */
    hr, div[data-testid="stDivider"] hr {
        border-color: var(--border) !important;
        background-color: var(--border) !important;
    }

    .vendor-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 0.55rem;
        border: 1px solid var(--border);
        background: var(--field);
        color: var(--text-main);
        font-size: 0.72rem;
        font-family: var(--font-mono);
        cursor: pointer;
        transition: all 0.15s;
    }

    .vendor-pill:hover {
        border-color: var(--primary);
        background: var(--bg-card);
    }

    .vendor-pill.active {
        border-color: var(--primary);
        background: rgba(12, 68, 124, 0.08);
    }

    .vendor-pill img {
        width: 14px;
        height: 14px;
        border-radius: 2px;
    }

    .section-label {
        font-family: var(--font-mono);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted);
        margin-bottom: 8px;
    }

    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 0.6rem !important;
    }

    .stDataFrame th {
        background-color: var(--field) !important;
        color: var(--text-muted) !important;
        font-family: var(--font-mono) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    .stDataFrame td {
        font-family: var(--font-mono) !important;
        font-size: 0.8125rem !important;
        color: var(--text-main) !important;
    }

    .nav-link {
        position: fixed;
        top: 12px;
        right: 24px;
        z-index: 9999;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.5rem 0.85rem;
        border-radius: 0.55rem;
        border: none;
        background: var(--primary);
        color: var(--sand);
        font-size: 0.8rem;
        font-weight: 600;
        font-family: var(--font-display);
        text-decoration: none;
        transition: background 0.15s ease, transform 0.15s ease;
    }

    .nav-link:hover {
        background: var(--primary-hover);
        transform: translateY(-1px);
        color: var(--sand);
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
st.caption("// detect all JS loaded on a page, incl. GTM-injected")


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
    st.markdown('<p class="section-label">// vendors detected</p>', unsafe_allow_html=True)

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
    st.markdown('<p class="section-label">// filter scripts</p>', unsafe_allow_html=True)

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
    st.caption(f"// scanned at {st.session_state.scanned_at}")

    # Export
    st.download_button(
        label="Download JSON",
        data=json.dumps(scripts, indent=2),
        file_name=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )
