#!/usr/bin/env python3
"""Audit Magento 2 / Mage-OS storefront URLs over HTTP.

Fetches each URL twice (cold + warm), measures TTFB and payload size, and parses
the cache-relevant response headers (X-Magento-Cache-Debug, Age, X-Varnish/Via,
Cache-Control, Content-Encoding, Set-Cookie). Emits findings with severities that
feed the scoring rubric in references/scoring.md.

Stdlib only — no pip installs needed.

Usage:
    python check-headers.py https://store.example/ [more URLs...]
        [--requests 2] [--insecure] [--json] [--timeout 30]

Typical URL set for an audit: homepage, one category page, one product page,
one CMS page. Do NOT pass cart/checkout/account URLs — those are private by
design and a MISS there is correct.
"""
from __future__ import annotations

import argparse
import gzip
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field

UA = "Mozilla/5.0 (compatible; magento-audit/1.0; +https://github.com/staksoft/magento-claude-skills)"

# TTFB thresholds (seconds) for a *cached* page. An FPC/Varnish hit should be
# served without touching PHP, so anything slower points at the cache not working
# or the server in front of it.
TTFB_HIT_WARN = 0.3
TTFB_HIT_CRIT = 1.0
# For an uncached (MISS) page PHP runs, so the bar is lower.
TTFB_MISS_WARN = 1.5
TTFB_MISS_CRIT = 3.0

HTML_SIZE_WARN = 350 * 1024   # uncompressed HTML document size
HTML_SIZE_CRIT = 1024 * 1024


@dataclass
class Fetch:
    url: str
    status: int = 0
    ttfb: float = 0.0
    total: float = 0.0
    body_bytes: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def fetch(url: str, timeout: float, insecure: bool) -> Fetch:
    """GET a URL, returning timing + lowercased headers. TTFB is measured to the
    moment response headers are available (urlopen returns), total to body read."""
    result = Fetch(url=url)
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip, deflate",
    })
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            result.ttfb = time.perf_counter() - start
            body = resp.read()
            result.total = time.perf_counter() - start
            result.status = resp.status
            result.headers = {k.lower(): v for k, v in resp.headers.items()}
            enc = result.headers.get("content-encoding", "")
            if enc == "gzip":
                body = gzip.decompress(body)
            elif enc == "deflate":
                body = zlib.decompress(body)
            result.body_bytes = len(body)
    except urllib.error.HTTPError as e:
        result.ttfb = result.total = time.perf_counter() - start
        result.status = e.code
        result.headers = {k.lower(): v for k, v in e.headers.items()}
        result.error = f"HTTP {e.code}"
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as e:
        result.error = str(e)
    return result


def behind_varnish(h: dict[str, str]) -> bool:
    return "x-varnish" in h or "varnish" in h.get("via", "").lower()


def analyze(url: str, fetches: list[Fetch]) -> list[dict]:
    """Produce findings from the fetch sequence for one URL. The last fetch is the
    'warm' request — by then the page should be in FPC/Varnish."""
    findings: list[dict] = []

    def add(severity: str, finding: str, detail: str) -> None:
        findings.append({"url": url, "severity": severity, "finding": finding, "detail": detail})

    errors = [f for f in fetches if f.error]
    if errors and all(f.error for f in fetches):
        add("critical", "URL unreachable", errors[0].error or "request failed")
        return findings

    warm = fetches[-1]
    h = warm.headers
    debug = h.get("x-magento-cache-debug", "").upper()
    varnish = behind_varnish(h)
    age = h.get("age")
    served_from_cache = debug == "HIT" or (varnish and age not in (None, "0", ""))

    # --- cache state -----------------------------------------------------
    if debug == "MISS" and not varnish:
        add("critical", "Page not served from full-page cache",
            "X-Magento-Cache-Debug: MISS on a warm request. Either FPC is disabled, the page "
            "contains a cacheable=\"false\" block (run scan-layout.py), or the request varies "
            "per-visitor (cookies in the cache key). See references/fpc-audit.md.")
    elif varnish and age in ("0", None, "") and debug != "HIT":
        add("critical", "Varnish present but not caching this page",
            "Age header is 0/absent on a warm request behind Varnish. Check that Magento's "
            "caching application is set to varnish (caching_application=2) and that the VCL "
            "is the one generated by bin/magento varnish:vcl:generate.")
    elif not debug and not varnish:
        add("medium", "Cache state not observable from headers",
            "Neither X-Magento-Cache-Debug nor Varnish headers present. Three possibilities: "
            "(a) production mode hides the debug header — judge by TTFB instead; (b) Varnish "
            "strips its headers — also fine; (c) full_page cache is DISABLED — Magento then "
            "emits no debug header at all, even in developer mode. If you have CLI access, "
            "settle it with: bin/magento cache:status (full_page must be 1).")

    if debug and "x-magento-tags" in h:
        add("low", "Cache debug headers exposed publicly",
            "X-Magento-Cache-Debug and X-Magento-Tags are visible to visitors. Harmless "
            "functionally but leaks catalog structure; production Varnish VCL normally "
            "unsets them. Skip this finding for local/dev environments.")

    # --- timing ----------------------------------------------------------
    warn, crit = (TTFB_HIT_WARN, TTFB_HIT_CRIT) if served_from_cache else (TTFB_MISS_WARN, TTFB_MISS_CRIT)
    label = "cache hit" if served_from_cache else "uncached page"
    if warm.ttfb >= crit:
        add("high", f"TTFB {warm.ttfb:.2f}s on a {label}",
            f"Threshold {crit:.1f}s. " + (
                "A cache hit this slow means the cache backend or web server in front is the "
                "bottleneck (Redis latency, server overload, TLS termination) — see "
                "references/server-config.md."
                if served_from_cache else
                "PHP execution is slow: check OPcache, Redis, MySQL, and third-party "
                "modules. Profile before optimizing — see references/server-config.md."))
    elif warm.ttfb >= warn:
        add("medium", f"TTFB {warm.ttfb:.2f}s on a {label}", f"Above the {warn:.1f}s comfort threshold.")

    if len(fetches) >= 2 and not fetches[0].error:
        cold = fetches[0]
        if served_from_cache and cold.ttfb > 0 and cold.ttfb / max(warm.ttfb, 0.001) > 5:
            add("info", f"Cold {cold.ttfb:.2f}s vs warm {warm.ttfb:.2f}s",
                "Large cold/warm gap is normal, but if real traffic often sees cold pages, "
                "consider a cache warmer after cache flushes/deploys.")

    # --- payload ---------------------------------------------------------
    if "content-encoding" not in h and warm.body_bytes > 20 * 1024:
        add("high", "HTML served without compression",
            "No Content-Encoding despite Accept-Encoding: gzip. Enable gzip/brotli in "
            "nginx/Varnish — this is a one-line fix with a large transfer-size win.")
    if warm.body_bytes >= HTML_SIZE_CRIT:
        add("high", f"HTML document is {warm.body_bytes // 1024} KB uncompressed",
            "Over 1 MB of HTML usually means inlined data/SVG bloat or a runaway widget. "
            "See references/frontend-perf.md.")
    elif warm.body_bytes >= HTML_SIZE_WARN:
        add("medium", f"HTML document is {warm.body_bytes // 1024} KB uncompressed",
            "Large for a storefront page; check for inlined config/styles.")

    if warm.status >= 400:
        add("critical", f"HTTP {warm.status}", "Page errors out; nothing else on it can be judged.")
    elif warm.status in (301, 302):
        add("medium", f"Audited URL redirects ({warm.status})",
            f"Re-run against the final URL: {h.get('location', '?')}")

    if not findings:
        add("ok", "Page healthy",
            f"Served from cache ({'Varnish' if varnish else 'built-in FPC'}), "
            f"TTFB {warm.ttfb:.2f}s, {warm.body_bytes // 1024} KB.")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="+", help="Storefront URLs to audit (public pages only)")
    parser.add_argument("--requests", type=int, default=2, help="Requests per URL (default 2: cold+warm)")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification (local/dev certs)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    report = []
    for url in args.urls:
        fetches = [fetch(url, args.timeout, args.insecure) for _ in range(max(args.requests, 1))]
        warm = fetches[-1]
        entry = {
            "url": url,
            "status": warm.status,
            "ttfb_cold": round(fetches[0].ttfb, 3),
            "ttfb_warm": round(warm.ttfb, 3),
            "total_warm": round(warm.total, 3),
            "html_kb": warm.body_bytes // 1024,
            "cache_debug": warm.headers.get("x-magento-cache-debug"),
            "varnish": behind_varnish(warm.headers),
            "age": warm.headers.get("age"),
            "content_encoding": warm.headers.get("content-encoding"),
            "findings": analyze(url, fetches),
        }
        report.append(entry)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for e in report:
            print(f"\n== {e['url']}")
            print(f"   status={e['status']}  ttfb cold/warm={e['ttfb_cold']}s/{e['ttfb_warm']}s  "
                  f"html={e['html_kb']}KB  cache-debug={e['cache_debug']}  "
                  f"varnish={e['varnish']}  age={e['age']}  encoding={e['content_encoding']}")
            for f in e["findings"]:
                print(f"   [{f['severity'].upper():8}] {f['finding']}")
                print(f"              {f['detail']}")

    return 0  # informational tool; findings are the output, not the exit code


if __name__ == "__main__":
    sys.exit(main())
