# Script Auditor

Detect every JavaScript script loaded on a webpage — including tags **injected by Google Tag Manager after page load** — and identify their vendor (GA4, Hotjar, Facebook Pixel, HubSpot, etc.).

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![Playwright](https://img.shields.io/badge/playwright-chromium-green)
![Flask](https://img.shields.io/badge/flask-3.x-lightgrey)
![Streamlit](https://img.shields.io/badge/streamlit-1.x-red)

---

## Features

- 🔍 Detects **all scripts**: inline, external, and dynamically injected
- 🏷️ **GTM-aware**: flags scripts loaded by Google Tag Manager
- 🏢 **1200+ domains** mapped via DuckDuckGo Tracker Radar + pattern matching
- 🖱️ **User interactions**: auto-clicks cookie consent banners, scrolls page to trigger lazy-loaded scripts
- 🌐 **V1 Web UI** (Flask) — opencode-styled dark theme with vendor filtering, icons, SSE progress
- 📊 **V2 Web UI** (Streamlit) — data tables with built-in sorting, filtering, export
- 💻 **CLI mode** for terminal use and batch processing
- 📄 JSON output for every scan

---

## Quick Start

### Start both UIs (one command)

```bash
python3 start.py
```

On first run this creates the `venv/`, installs dependencies, and installs
Playwright's Chromium (best-effort), then launches both apps. It works whether
or not the venv is activated — no manual setup needed.

> A browser is only required to run an actual audit, not to launch the apps.
> Where Playwright's Chromium can't be installed (e.g. some Linux distros), the
> apps fall back to a system **Google Chrome** install, launched via
> `channel="chrome"`.

<details>
<summary>Manual setup (optional)</summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
```
</details>

| App | URL | Description |
|-----|-----|-------------|
| **V1 (Flask)** | http://localhost:7070 | Full-featured SPA with SSE streaming |
| **V2 (Streamlit)** | http://localhost:8501 | Data table view with sorting/filtering |

### 3. Or use the CLI

```bash
# Single URL
python3 audit_scripts.py https://example.com --verbose

# Multiple URLs from file
python3 audit_scripts.py --file urls.txt --output results.json

# Disable interactions
python3 audit_scripts.py https://example.com --no-click-consent --no-scroll

# Options
python3 audit_scripts.py --help
```

---

## CLI Reference

```
python3 audit_scripts.py <url>                  Single URL
python3 audit_scripts.py --file FILE            Batch mode (one URL per line)
python3 audit_scripts.py --output FILE          Output JSON path
python3 audit_scripts.py --timeout N            Seconds per URL (default: 30)
python3 audit_scripts.py --no-headless          Show browser window
python3 audit_scripts.py --verbose              Print full script table
python3 audit_scripts.py --no-click-consent     Skip cookie consent clicks
python3 audit_scripts.py --no-scroll            Skip page scrolling
python3 audit_scripts.py --scroll-count N       Number of scroll steps (default: 3)
```

### Output Format

```json
{
  "url": "https://example.com",
  "scanned_at": "2026-05-18T10:00:00Z",
  "gtm_detected": true,
  "scripts": [
    {
      "url": "https://www.googletagmanager.com/gtm.js?id=GTM-XXXX",
      "name": "gtm.js",
      "vendor": "Google Tag Manager",
      "via_gtm": false,
      "type": "external",
      "blocked": false
    },
    {
      "url": "https://static.hotjar.com/c/hotjar-XXXXX.js",
      "name": "hotjar-XXXXX.js",
      "vendor": "Hotjar",
      "via_gtm": true,
      "type": "external",
      "blocked": false
    }
  ]
}
```

---

## How It Works

1. **Playwright** launches headless Chromium and intercepts all network requests
2. Navigates with `wait_until="networkidle"`, then waits 2s for late-firing GTM tags
3. **User interactions**: clicks cookie consent buttons, scrolls page to trigger lazy scripts
4. **Diffs** network-captured scripts against DOM `<script src>` snapshot:
   - In DOM = loaded from HTML directly
   - Network only = injected dynamically (flagged `via_gtm: true` when GTM present)
5. Inline `<script>` blocks scanned for vendor fingerprints (`fbq(`, `gtag(`, `_hsq`, etc.)
6. Every script URL matched against **DuckDuckGo Tracker Radar** (1200+ domains) + pattern fallback

---

## Vendor Coverage

| Category | Vendors |
|---|---|
| Analytics | Google Analytics (UA + GA4), Mixpanel, Amplitude, Heap, Segment |
| Tag Management | Google Tag Manager |
| Marketing | Facebook Pixel, LinkedIn Insight, Twitter/X, TikTok, Pinterest, Google Ads, Criteo, Outbrain, Taboola |
| Heatmaps/Session | Hotjar, Microsoft Clarity, Crazy Egg, Lucky Orange, FullStory, Mouseflow, Glassbox |
| CRM / Support | HubSpot, Intercom, Drift, Zendesk, Crisp |
| Product Analytics | Pendo, Qualaroo |
| Error/Monitoring | Sentry, Datadog, New Relic |
| Payments | Stripe |
| Consent (CMP) | OneTrust, Cookiebot, Didomi |
| CDN Libraries | jQuery, Google Hosted, Cloudflare CDNJS, jsDelivr, unpkg |
| Other | Yandex, Baidu, Alibaba, Shopify, Vercel, Fastly, Akamai, Quantcast |

---

## Project Structure

```
script-auditor/
├── app.py                  # Flask web app (V1)
├── streamlit_app.py        # Streamlit web app (V2)
├── start.py                # Start both apps together
├── audit_scripts.py        # Core audit engine + CLI
├── vendor_map.py           # Vendor detection (Tracker Radar + patterns)
├── vendor_db.json          # Bundled domain→vendor mapping (DuckDuckGo)
├── requirements.txt
├── gunicorn.conf.py        # Production server config
├── static/
│   ├── icon.svg            # App icon (SVG)
│   ├── favicon.ico         # Favicon
│   ├── icon-*.png          # App icons (all sizes)
│   └── manifest.json       # PWA manifest
├── templates/
│   └── index.html          # V1 UI (Flask)
└── deploy/
    ├── setup.sh            # VPS install script
    ├── script-auditor.service
    └── nginx.conf
```

---

## Deploy on a Linux VPS

### One-shot setup

```bash
git clone https://github.com/palbertus/script-auditor.git /tmp/script-auditor
cd /tmp/script-auditor
bash deploy/setup.sh
```

Stack: `Internet → Nginx → Gunicorn → Flask → Playwright Chromium`

### Management

```bash
systemctl status script-auditor     # check status
systemctl restart script-auditor    # restart after changes
journalctl -u script-auditor -f     # live logs
```

### HTTPS (Let's Encrypt)

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

---

## Requirements

- Python 3.9+
- Chromium (via `playwright install chromium`)
- ~300 MB disk space for Chromium binary
