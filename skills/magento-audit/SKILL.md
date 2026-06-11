---
name: magento-audit
description: >-
  (Coming soon — phase 2, not yet implemented.) Performance audit of a Magento 2 / Mage-OS
  storefront: full-page cache leaks (cacheable="false"), indexer and cron health, Varnish/
  Redis configuration, and frontend Core Web Vitals. Do not trigger yet; for Magento
  development tasks use the magento-module skill instead.
---

# Magento Storefront Audit (Phase 2 — stub)

This skill is planned but not yet implemented. Planned scope:

- **URL mode**: fetch store pages, inspect `X-Magento-Cache-Debug` / Varnish headers, TTFB,
  payload sizes, Core Web Vitals → severity-ranked report
- **Codebase mode**: scan layout XML for FPC-killers (`cacheable="false"`), check `env.php`
  cache/session config, indexer modes, cron health
- Scripts: `check-headers.py`, `scan-layout.py`
- Scoring rubric with severity levels and exact fix instructions

Until implemented, use the debugging and frontend references in the `magento-module` skill
for performance questions.
