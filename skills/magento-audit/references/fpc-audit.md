# Full-Page Cache Audit

FPC is the single biggest performance lever in Magento: a hit is served in tens of
milliseconds without booting PHP; a miss costs 0.5–3s of PHP execution. Most "Magento is
slow" complaints are really "FPC isn't working" complaints. Audit FPC first, always.

## How FPC decides

A page is stored in FPC only if **every** block in its layout is cacheable. One block with
`cacheable="false"` anywhere in the merged layout makes the whole page uncacheable —
silently. There is no warning, no log entry; the page just always MISSes.

The cache key includes the URL plus the `X-Magento-Vary` cookie (store, currency, customer
group context). Anything that forces per-visitor HTML on a cached page must instead be
loaded after page load via **customer-data sections** (the `Magento_Customer` JS that
populates the cart counter, welcome message, etc.) — that's how a personalized-looking page
stays cacheable.

## Reading the headers (URL mode)

Run `scripts/check-headers.py` against the homepage, a category page, a product page, and a
CMS page. Interpretation:

| Signal | Meaning |
|---|---|
| `X-Magento-Cache-Debug: HIT` | Built-in FPC serving the page. Good. |
| `X-Magento-Cache-Debug: MISS` on 2nd request | FPC broken for this page → codebase mode, find the killer |
| `Age: <n>` (n > 0) behind Varnish | Varnish hit. Good. |
| `Age: 0` always, Varnish present | Varnish never caches → wrong `caching_application` or broken VCL |
| `X-Magento-Cache-Debug` visible in production | VCL isn't stripping debug headers (info leak, low severity) |
| No cache headers at all | Production mode hides the debug header, **or** Varnish strips its own, **or** FPC is disabled — Magento emits no debug header at all when `full_page` is off (verified: it does not send MISS). Settle with `bin/magento cache:status` |

Built-in FPC still emits a `PHPSESSID` cookie on HIT responses in some setups — a session
cookie alone does **not** prove the page missed the cache.

Never audit cart/checkout/account URLs for cache hits: they are private by design and MISS
is correct there.

## Finding the killer (codebase mode)

```bash
python scripts/scan-layout.py /path/to/magento            # your code + themes
python scripts/scan-layout.py /path/to/magento --include-vendor   # + extensions
```

Severity logic the script applies:

- **`default.xml` with `cacheable="false"`** → critical. Applies to every page; FPC is
  effectively off store-wide. This is the classic third-party-extension bug.
- **Catalog/CMS/search handles** (`catalog_product_view`, `cms_index_index`, …) → critical.
  Your highest-traffic pages bypass cache.
- **Other public handles** → high. Verify intent.
- **Checkout/customer/sales handles** → info. Uncacheable by design; correct.

If the scan is clean but pages still MISS, the killer is being added at runtime:

1. `grep -rn "isScopePrivate\|cacheable" app/code vendor/<suspect>` — a block class
   returning `isScopePrivate(): true` has the same effect as `cacheable="false"`.
2. Sessions started in a block/plugin during page render also depersonalize the page —
   grep suspect extensions for `SessionManagerInterface`/`checkoutSession` usage in
   frontend blocks.
3. Bisect: `bin/magento module:disable Suspect_Module && bin/magento cache:flush`, re-test
   the URL, repeat. Fastest path when an extension is suspected.

## Fixing a cacheable="false" finding

Never just delete the attribute — the block was marked uncacheable because its output is
per-visitor. Choose the right refactor:

1. **Customer-data section (preferred, works with built-in FPC and Varnish).** Render the
   block as a static skeleton; populate the dynamic part client-side from a section. New
   section = `di.xml` entry under `sectionSourceMap` + a section source class + Knockout/JS
   binding. This is how core renders the mini-cart on cached pages.
2. **AJAX endpoint.** Skeleton HTML + a controller returning JSON, fetched on load. Simpler
   than sections for one-off data, but adds a request.
3. **ESI (Varnish only).** Set the block's `ttl="…"` attribute in layout XML; Varnish will
   fetch that fragment separately. Only worth it for fragments shared across visitors with
   a different TTL than the page (e.g. a stock ticker). Per-visitor content does NOT belong
   in ESI.
4. **It genuinely is a private page** → leave it, exclude the handle from the report.

## Cache invalidation health

Over-aggressive flushing is the other way FPC "doesn't work" — hit rate is low because
something flushes constantly:

- Check for `cache:flush`/`cache:clean` in deploy scripts and cron jobs. Deploys should
  flush; nothing else should on a schedule.
- Extensions calling `$cacheManager->flush()` or invalidating `full_page` on every save:
  `grep -rn "full_page" app/code vendor/<suspects> --include=*.php | grep -vi test`.
- Mass product imports invalidate cache tags for every touched product/category — expected,
  but schedule imports off-peak and consider a cache warmer afterwards.
- TTL: `system/full_page_cache/ttl` (default 86400). A tiny value here (some "optimization"
  guides suggest it) guts hit rate. Check with
  `bin/magento config:show system/full_page_cache/ttl`.

## Quick state checks (CLI)

```bash
bin/magento cache:status                  # full_page must be enabled
bin/magento config:show system/full_page_cache/caching_application
                                          # 1 = built-in, 2 = Varnish; empty = default (1)
bin/magento deploy:mode:show              # production expected on a live store
```

Built-in FPC vs Varnish: built-in stores pages in the Magento cache backend (file/Redis)
and still boots a slim PHP path on every hit. Varnish serves hits without touching PHP at
all and supports ESI. Any store with real traffic should run Varnish; built-in FPC is
acceptable for small stores and dev. If `caching_application` is 2 but no Varnish headers
appear in URL mode, the VCL or the proxy chain is broken — see
[server-config.md](server-config.md).
