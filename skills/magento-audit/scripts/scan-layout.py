#!/usr/bin/env python3
"""Scan a Magento 2 / Mage-OS codebase for full-page-cache killers in layout XML.

One block with cacheable="false" makes the ENTIRE page handle uncacheable — and if
it sits in default.xml it disables FPC for every page on the store. This script
finds every such block, identifies the layout handle it applies to, and ranks the
severity (default.xml = critical, catalog/CMS handles = high, checkout/customer
handles = expected and reported as info).

Stdlib only — no pip installs needed.

Usage:
    python scan-layout.py /path/to/magento [--include-vendor] [--json]

By default scans app/code and app/design (your code + themes). --include-vendor
adds vendor/ — noisy because core modules legitimately use cacheable="false" on
private pages, but useful for auditing installed third-party extensions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Handles where cacheable="false" is by design: pages that are private per
# visitor and must never be in FPC. Findings on these are reported as "info".
EXPECTED_PRIVATE_PREFIXES = (
    "checkout_", "onepage", "multishipping_", "customer_account",
    "customer_address", "sales_order_", "sales_guest_", "wishlist_index",
    "paypal_", "braintree_", "review_customer", "newsletter_manage",
    "downloadable_customer", "vault_cards", "sales_billing_agreement",
    "persistent_index", "contact_index", "sendfriend_",
    "catalog_product_compare", "loginascustomer_",
)

# path fragments for test fixtures, never real merged layout
TEST_PATH_FRAGMENTS = ("/dev/tests/", "/_files/", "/Test/", "/tests/")

# core packages: their cacheable="false" usage (emails, RMA, shared wishlist, ...) is by
# design and audited upstream — scanning them only buries third-party findings in noise
TRUSTED_VENDOR_PREFIXES = ("vendor/magento/", "vendor/mage-os/")

CACHEABLE_FALSE_RE = re.compile(r"""cacheable\s*=\s*["']false["']""")


def classify(handle: str, rel_path: str) -> tuple[str, str]:
    """Return (severity, why) for a cacheable=false block on this handle."""
    if handle == "default":
        return ("critical",
                "default.xml applies to EVERY page — this single block disables full-page "
                "cache store-wide.")
    if handle in ("catalog_product_view", "catalog_category_view", "cms_index_index",
                  "cms_page_view", "catalogsearch_result_index"):
        return ("critical",
                f"{handle} is a high-traffic public page; it should always be FPC-cacheable. "
                "Move the dynamic part to customer-data (sections) JS or AJAX.")
    if any(handle.startswith(p) for p in EXPECTED_PRIVATE_PREFIXES):
        return ("info",
                "Private page — uncacheable by design. No action needed unless this handle "
                "was supposed to be public.")
    return ("high",
            "Public-looking handle made uncacheable. Verify whether this page should be in "
            "FPC; if yes, refactor the block (see references/fpc-audit.md).")


def handle_from_path(path: Path) -> str:
    """Layout file name == layout handle (minus .xml)."""
    return path.stem


def area_from_path(rel: str) -> str:
    if "/view/frontend/" in rel or "\\view\\frontend\\" in rel or "/frontend/" in rel:
        return "frontend"
    if "/view/adminhtml/" in rel or "\\view\\adminhtml\\" in rel or "/adminhtml/" in rel:
        return "adminhtml"
    return "base"


def blocks_with_cacheable_false(path: Path) -> list[str]:
    """Names of <block>/<referenceBlock> elements carrying cacheable="false".
    Falls back to a line-based report if the XML doesn't parse."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return ["<unparseable XML — inspect manually>"]
    names = []
    for el in root.iter():
        if el.get("cacheable") == "false":
            names.append(el.get("name") or el.get("class") or el.tag)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="Magento installation root (contains app/, vendor/)")
    parser.add_argument("--include-vendor", action="store_true",
                        help="Also scan vendor/ (audits installed extensions; core noise filtered by severity)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    scan_dirs = [root / "app" / "code", root / "app" / "design"]
    if args.include_vendor:
        scan_dirs.append(root / "vendor")

    findings: list[dict] = []
    scanned = 0
    for base in scan_dirs:
        if not base.is_dir():
            continue
        for path in base.rglob("*.xml"):
            # layout files live under a .../layout/ or .../page_layout/ directory
            if not {"layout", "page_layout"} & set(path.parent.parts):
                continue
            posix = path.as_posix()
            if any(frag in posix for frag in TEST_PATH_FRAGMENTS):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            scanned += 1
            if not CACHEABLE_FALSE_RE.search(text):
                continue
            rel = str(path.relative_to(root))
            handle = handle_from_path(path)
            area = area_from_path(rel)
            if area == "adminhtml":
                continue  # admin pages are never in FPC; not a finding
            severity, why = classify(handle, rel)
            rel_posix = rel.replace("\\", "/")
            in_vendor = rel_posix.startswith("vendor/")
            if in_vendor and severity == "info":
                continue  # private-by-design vendor usage is pure noise
            if in_vendor and rel_posix.startswith(TRUSTED_VENDOR_PREFIXES):
                continue  # core usage is by design; only third-party vendor code is a finding
            findings.append({
                "severity": severity,
                "handle": handle,
                "file": rel,
                "area": area,
                "vendor": in_vendor,
                "blocks": blocks_with_cacheable_false(path),
                "why": why,
            })

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["file"]))

    if args.json:
        print(json.dumps({"scanned_layout_files": scanned, "findings": findings}, indent=2))
    else:
        print(f"Scanned {scanned} layout XML files under {', '.join(str(d) for d in scan_dirs if d.is_dir())}")
        if not findings:
            print("No cacheable=\"false\" FPC-killers found outside admin. ✔")
        for f in findings:
            print(f"\n[{f['severity'].upper():8}] handle={f['handle']}  ({f['area']}{', vendor' if f['vendor'] else ''})")
            print(f"           {f['file']}")
            print(f"           blocks: {', '.join(f['blocks'])}")
            print(f"           {f['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
