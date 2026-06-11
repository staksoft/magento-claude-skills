# Frontend Performance & Core Web Vitals

Server-side caching gets TTFB right; Core Web Vitals (LCP, CLS, INP) are then decided by
what the theme ships to the browser. Luma-based themes are heavy by design — set
expectations accordingly and prioritize the fixes with the best effort/impact ratio.

## Measuring

- Lab: PageSpeed Insights / Lighthouse against the live URL (or `npx lighthouse <url>` if
  available). Field: Chrome UX Report data shown at the top of PSI — field data wins when
  they disagree.
- In URL mode without Lighthouse access, estimate from the HTML: `check-headers.py` reports
  document size; additionally count `<script src` / `<link rel="stylesheet"` occurrences in
  the fetched HTML and look for `rel=preload` on the hero image.

Typical Luma reality check: LCP 3–6s, INP poor on product pages. Don't promise sub-1s LCP
on Luma without a rebuild; do capture the achievable wins below.

## The big levers, in order

### 1. JavaScript strategy (Luma's curse)

Luma ships RequireJS and loads 100+ JS files unbundled, or — worse — with **built-in
bundling enabled**, one ~5–13 MB bundle on every page. Audit:

```bash
bin/magento config:show dev/js/enable_js_bundling     # 1 = the bad bundling → turn OFF
bin/magento config:show dev/js/merge_files
bin/magento config:show dev/js/minify_files           # should be 1 in production
```

- Built-in bundling enabled → **high**: disable it. It predates HTTP/2 and makes things
  worse on every modern setup.
- Proper fix tiers: (a) minify only — safe baseline; (b) advanced bundling via
  [magepack](https://github.com/magesuite/magepack) — real gains, some maintenance;
  (c) Hyvä theme — removes RequireJS/jQuery entirely, by far the largest CWV win available
  to a Magento store, but it's a theme rebuild, not an audit fix. Recommend it as the
  strategic option when the client owns the theme.
- Defer third-party tags (GTM payload audit): marketing tags routinely cost more INP than
  all of Magento's own JS. List them from the HTML and flag any synchronous ones.

### 2. CSS

```bash
bin/magento config:show dev/css/minify_files          # 1 expected in production
bin/magento config:show dev/css/use_css_critical_path # critical CSS toggle
```

Critical CSS (`use_css_critical_path=1`) inlines above-the-fold styles and defers the rest
— good LCP win on Luma, but verify the generated critical CSS actually matches the theme
(broken flash-of-unstyled-content otherwise). `merge_files` for CSS is mostly harmless but
redundant under HTTP/2.

### 3. Images — usually the LCP element

- Hero/product image not preloaded → add `<link rel="preload" as="image">` for the LCP
  image via layout XML head.
- No WebP/AVIF: core Magento still serves JPEG/PNG. Fix at the CDN/proxy layer (automatic
  format negotiation) or with an image-optimization module. Flag if `content-type` of
  product images is `image/jpeg` and sizes are large.
- `loading="lazy"` on below-fold images is default-ish in recent Luma; verify the LCP image
  is **not** lazy-loaded (classic self-inflicted LCP penalty).
- Oversized originals: catalog images served at upload resolution instead of the resized
  cache (`/media/catalog/product/cache/...` missing from URLs) → image resize cache broken
  or `catalog:images:resize` never run.

### 4. Fonts & CLS

- Fonts without `font-display: swap` block text paint.
- CLS culprits in order of frequency: images without width/height attributes, late-injected
  promo banners/cookie bars, web font swap. Lighthouse names the shifting elements — report
  those, not generalities.

### 5. Static content & delivery

```bash
bin/magento config:show dev/static/sign               # static signing: 1 expected
ls pub/static/frontend/<Vendor>/<theme>                # deployed for every locale?
```

- HTML/JS/CSS must arrive compressed (check-headers.py flags missing Content-Encoding) and
  with long-lived `Cache-Control` on `/static/` and `/media/` (set by nginx sample config;
  often lost on custom setups).
- No CDN on an international store → medium; static assets from a single origin add RTT to
  every asset for far-away users.

## Severity guide

| Finding | Severity |
|---|---|
| Built-in JS bundling on | high |
| JS/CSS minification off in production | medium |
| LCP image lazy-loaded or not preloaded | high |
| No compression on text assets | high |
| No WebP/CDN on image-heavy store | medium |
| Synchronous third-party tags | medium (high if >5) |
| Luma + "make LCP < 1.5s" expectation | flag honestly: needs Hyvä or heavy custom work |
