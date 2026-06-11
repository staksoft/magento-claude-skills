# Scoring Rubric & Report Format

Every audit ends in one markdown report, severity-ranked, with an exact fix per finding.
The reader is a developer or store owner deciding what to do Monday morning — rank by
impact-per-effort, not by how interesting the finding is.

## Severity definitions

| Severity | Definition | Examples |
|---|---|---|
| **Critical** | Caching or background processing is broken store-wide; fixing this changes everything else's numbers | FPC disabled / `cacheable="false"` in default.xml; cron not running; developer mode in production; Varnish present but 0% hit rate; missing `http_cache_hosts` (stale content) |
| **High** | Major measurable cost on high-traffic pages or core flows | Product/category handle uncacheable; all indexers realtime; sessions on files (multi-server); no OPcache; built-in JS bundling on; no compression; LCP image lazy-loaded |
| **Medium** | Real but bounded cost, or risk rather than current pain | Shared Redis DB for cache+sessions; minification off; no CDN/WebP; cron history bloat; synchronous marketing tags |
| **Low** | Hygiene; fix opportunistically | Debug headers exposed publicly; flat catalog enabled; redundant CSS merging |
| **Info** | Correct behavior worth stating so nobody "fixes" it | checkout/customer handles uncacheable; cold-request slowness with healthy warm hits |

When unsure between two severities, ask: *if only this one thing were fixed, would the
store's p75 numbers visibly move?* Yes → high or above.

## Score (0–100)

Start at 100, subtract per finding: critical −25, high −10, medium −4, low −1 (floor 0).
Cap the label, don't let math hide a broken store: any critical present → grade is at most
**D** regardless of score.

| Score | Grade |
|---|---|
| 90–100 | A — production-ready |
| 75–89 | B — solid, targeted fixes |
| 50–74 | C — significant headroom |
| 25–49 | D — caching/infra problems dominate |
| 0–24 | F — store is effectively running uncached |

The score is a communication device, not a measurement — always present it alongside the
top three findings, never alone.

## Report template

```markdown
# Storefront Performance Audit — <store / repo>
<date> · mode: URL / codebase / combined · pages tested: <n>

## Score: <n>/100 (<grade>)
<one-sentence verdict: the single most important thing to fix>

## Findings

### 🔴 Critical
#### 1. <finding title>
- **Evidence**: <header value / file:line / CLI output — verbatim, so it's verifiable>
- **Impact**: <what it costs, concretely>
- **Fix**: <exact command / file change / refactor approach>
- **Effort**: <S/M/L>

### 🟠 High
...same structure...

### 🟡 Medium / 🔵 Low
<one line each: finding — fix — effort>

### ℹ️ Working as intended
<things that look alarming but are correct, e.g. checkout pages uncached>

## Suggested order of work
1. <fix> — unlocks <what>
2. ...

## Not audited
<what this audit could not see: e.g. no server access, so PHP/MySQL config unchecked;
no field CWV data; load behavior under traffic>
```

## Rules for writing findings

- **Evidence is verbatim and reproducible.** Quote the actual header, the file path and
  line, the CLI output. The reader must be able to re-check every claim.
- **One fix per finding**, the best one — not a menu. If a strategic alternative exists
  (e.g. Hyvä vs magepack), put it in one sentence after the tactical fix.
- **Never recommend disabling caching, debug modes in production, or "flush cache via
  cron".** If a finding's obvious quick fix is harmful, say so explicitly.
- **State the blind spots.** A URL-only audit can't see env.php; a codebase audit can't
  see real TTFB. The "Not audited" section is mandatory — it's what keeps the report
  honest and scopes follow-up work.
- Findings on a dev/staging environment: drop the production-only checks (debug headers,
  developer mode) to info, and say the numbers need re-measuring on production infra.
