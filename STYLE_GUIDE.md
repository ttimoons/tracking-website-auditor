# Data & Play — Design System

A light, Swiss-modern UI kit: cream paper, ink text, flat colour blocks, hairline
rules, oversized display type, and small monospace "code-comment" labels. Built to
be dropped into any app (React/Next, plain HTML, etc.). No CSS framework required —
just custom properties + a handful of component classes.

> Origin: distilled from the "Patrice — Data & Play" poster system. The look is
> deliberately *flat* — no glassmorphism, no blur, no soft drop shadows. Depth comes
> from solid paper surfaces, 1px ink rules, and colour.

---

## 1. Principles

- **Paper, not glass.** Surfaces are solid warm-cream. Cards sit on a slightly
  darker page with a hairline border — no translucency or backdrop-blur.
- **Two typefaces, clear jobs.** *Space Grotesk* for everything structural
  (headings, numbers, body); *JetBrains Mono* only for small UPPERCASE labels,
  metadata, axes, and code — often prefixed `//` like a comment.
- **Tight display type.** Headings and big numbers use negative letter-spacing
  (`-0.03` to `-0.06em`) and sit large.
- **Flat colour blocks.** Accent colours are used as full-bleed fills (tiles,
  buttons, status), not gradients.
- **Hairline rules.** Dividers are 1px ink lines at low opacity, never heavy.
- **Engineering-paper grid.** The page background carries a faint 28px grid for a
  "wireframe" feel; opaque cards cover it.

---

## 2. Fonts

Variable fonts: **Space Grotesk** (display) + **JetBrains Mono** (mono).

### Next.js (`next/font/google`) — self-hosted, no layout shift

```tsx
// app/layout.tsx
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

### Plain HTML fallback

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
  rel="stylesheet"
/>
```

The token block below references the Next CSS variables with literal fallbacks, so
it works either way.

---

## 3. Design tokens — copy this `:root` block

```css
:root {
  /* Brand palette */
  --slate:    #0C447C;  /* deep blue — primary brand / links */
  --teal:     #1D9E75;  /* green — positive / inflow / "live" */
  --graphite: #5F5E5A;  /* muted text */
  --sand:     #F1EFE8;  /* light text on dark blocks */
  --violet:   #534AB7;
  --coral:    #D85A30;  /* warm accent — CTA / negative / outflow */
  --magenta:  #D4537E;
  --amber:    #BA7517;
  --paper:    #F1EFE8;  /* card surface */
  --ink:      #2C2C2A;  /* primary text */

  /* Semantic tokens — reference these in components, not raw hex */
  --primary:      var(--slate);
  --primary-hover:#0A3866;
  --bg-dark:      #E8E4DC;      /* page background (warm paper) */
  --bg-card:      var(--paper); /* solid card surface */
  --field:        #FBFAF6;      /* near-white input surface */
  --text-main:    var(--ink);
  --text-muted:   var(--graphite);
  --border:       rgba(44, 44, 42, 0.16);  /* hairline rule */
  --border-faint: rgba(44, 44, 42, 0.08);
  --accent:       var(--teal);   /* positive */
  --error:        var(--coral);  /* negative / error */

  --font-display: var(--font-space-grotesk), "Space Grotesk", system-ui, sans-serif;
  --font-mono:    var(--font-jetbrains-mono), "JetBrains Mono", ui-monospace, monospace;

  color-scheme: light;
}
```

### Colour semantics

| Token        | Hex       | Use                                            |
| ------------ | --------- | ---------------------------------------------- |
| `--primary`  | `#0C447C` | Buttons, links, active states, user chat bubble |
| `--accent`   | `#1D9E75` | Positive values, inflow, "live" status dots     |
| `--error`    | `#D85A30` | Negative values, outflow, errors, playful CTAs  |
| `--ink`      | `#2C2C2A` | Primary text                                    |
| `--graphite` | `#5F5E5A` | Secondary / muted text, mono labels             |
| `--paper`    | `#F1EFE8` | Card surfaces                                   |
| `--bg-dark`  | `#E8E4DC` | Page background                                 |
| `--sand`     | `#F1EFE8` | Text/icons on coloured (dark) fills             |

Extra palette colours (`--violet --magenta --amber`) are for data viz / multi-tile
layouts. See the chart palette in §6.

---

## 4. Base layer

```css
* { box-sizing: border-box; padding: 0; margin: 0; -webkit-tap-highlight-color: transparent; }

body {
  background-color: var(--bg-dark);
  color: var(--text-main);
  font-family: var(--font-display);
  letter-spacing: -0.01em;
  /* faint engineering-paper grid — opaque cards cover it */
  background-image:
    linear-gradient(rgba(44, 44, 42, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(44, 44, 42, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
}

h1 { font-family: var(--font-display); font-weight: 700; letter-spacing: -0.035em; }
p  { color: var(--text-muted); }

/* Small uppercase code-comment label — the signature accent of this system */
.mono { font-family: var(--font-mono); letter-spacing: 0.04em; }
```

Typical mono label usage (note the `//` prefix and uppercasing):

```html
<div class="mono" style="text-transform:uppercase; font-size:.72rem; color:var(--graphite)">
  // net · all accounts
</div>
```

---

## 5. Components

### Flat paper card

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  box-shadow: 0 1px 0 rgba(44, 44, 42, 0.04); /* barely-there */
}
```

### Buttons

```css
.btn-primary {
  background: var(--primary);
  color: var(--sand);
  font-family: var(--font-display);
  font-weight: 700;
  border: none;
  border-radius: 0.6rem;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-primary:hover    { background: var(--primary-hover); transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.45; cursor: default; transform: none; }

/* Compact header CTA (slate fill, sand text, icon + label) */
.header-cta {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: var(--primary); color: var(--sand);
  font-family: var(--font-display); font-size: 0.8rem; font-weight: 600;
  text-decoration: none; white-space: nowrap;
  padding: 0.5rem 0.85rem; border-radius: 0.55rem;
  transition: background 0.15s ease, transform 0.15s ease;
}
.header-cta:hover { background: var(--primary-hover); transform: translateY(-1px); }
```

For a playful CTA / floating action button, swap the fill to `var(--coral)`.

### Inputs & selects

```css
.control-input {
  width: 100%;
  background: var(--field);
  border: 1px solid var(--border);
  border-radius: 0.6rem;
  padding: 0.75rem 1rem;
  color: var(--text-main);
  font-family: inherit;
  appearance: none;
}
.control-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(12, 68, 124, 0.12); /* slate focus ring */
}
/* select chevron — graphite stroke */
select.control-input {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235F5E5A' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 1rem center; padding-right: 2.5rem;
}
```

### Field label (mono, uppercase)

```css
.field-label {
  font-family: var(--font-mono);
  font-size: 0.68rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-muted);
}
```

### KPI / big number (the "scorecard" pattern)

```css
.kpi-label { /* small mono cap */
  font-family: var(--font-mono); text-transform: uppercase;
  font-size: 0.72rem; letter-spacing: 0.06em; color: var(--text-muted);
}
.kpi-value { /* oversized, tight display */
  font-family: var(--font-display); font-size: 2rem; font-weight: 700;
  letter-spacing: -0.04em; color: var(--accent); /* or --error when negative */
}
```

Colour the value by sign: `var(--accent)` for positive, `var(--error)` for negative.

### Hairline rule / divider

```css
.rule      { height: 1px; background: var(--border); }
.rule-faint{ height: 1px; background: var(--border-faint); }
```

### Status dot

```html
<span class="mono" style="text-transform:uppercase; font-size:.7rem">
  status · <span style="color:var(--teal)">● live</span>
</span>
```

### Chat bubbles

```css
/* user: slate fill + sand text · assistant: near-white field + hairline border */
.bubble-user      { background: var(--primary); color: var(--sand); border-radius: 0.85rem; }
.bubble-assistant { background: var(--field); color: var(--text-main);
                    border: 1px solid var(--border); border-radius: 0.85rem; }
```

---

## 6. Data visualisation

Series palette (order matters — first series gets the first colour):

```js
const CHART_PALETTE = [
  "#1D9E75", // teal
  "#0C447C", // slate
  "#D85A30", // coral
  "#534AB7", // violet
  "#BA7517", // amber
  "#D4537E", // magenta
  "#5F5E5A", // graphite
  "#2C2C2A", // ink
];
```

Axis / grid styling on light paper:

```css
.chart-grid  { stroke: rgba(44, 44, 42, 0.10); }
.chart-zero  { stroke: rgba(44, 44, 42, 0.32); stroke-dasharray: 3 3; }
.chart-axis  { fill: var(--text-muted); font-family: var(--font-mono); font-size: 10px; }
.chart-title { fill: var(--text-main); font-family: var(--font-display); font-weight: 700; }
.pie-slice   { stroke: var(--bg-card); stroke-width: 1.5px; } /* gaps in paper colour */
```

---

## 7. Markdown / tables

```css
.md code { font-family: var(--font-mono); background: rgba(44,44,42,0.07);
           padding: .1rem .3rem; border-radius: .35rem; }
.md pre  { background: rgba(12,68,124,0.06); border: 1px solid var(--border-faint);
           border-radius: .6rem; padding: .6rem; }
.md th   { font-family: var(--font-mono); text-transform: uppercase; font-size: .68rem;
           letter-spacing: .03em; background: rgba(12,68,124,0.06); }
.md td, .md th { border: 1px solid var(--border); padding: .35rem .55rem; }
.md tbody tr:nth-child(even) { background: rgba(44,44,42,0.025); }
```

---

## 8. Reuse checklist (dropping this into a new app)

1. Load the two fonts (§2) and expose them as `--font-space-grotesk` /
   `--font-jetbrains-mono` (or rely on the literal fallbacks in the token block).
2. Paste the `:root` token block (§3) into your global stylesheet.
3. Paste the base layer (§4) — body bg + grid + the `.mono` helper.
4. Pull in only the component classes you need (§5–7); they all reference tokens, so
   re-theming is just editing `:root`.
5. **Conventions to keep the look consistent:**
   - Big/structural text → `--font-display`, tight tracking. Small labels/meta →
     `--font-mono`, uppercase, `0.04–0.06em` tracking, often `//`-prefixed.
   - Surfaces are solid `--paper` with a `--border` hairline. No blur, no gradients.
   - Positive = `--accent` (teal), negative/CTA = `--error`/`--coral`, brand = `--primary` (slate).
   - Dividers are 1px at `--border` / `--border-faint` opacity.
   - Set `color-scheme: light` so native controls (date pickers, scrollbars) render light.
```
