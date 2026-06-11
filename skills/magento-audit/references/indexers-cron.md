# Indexers & Cron Health

Indexers and cron are the background half of Magento performance. Broken cron means stale
indexes, unsent emails, no sitemap, and an exploding `cron_schedule` table; wrong indexer
modes mean admin saves take seconds and bulk operations crawl.

## Indexer modes — the #1 finding

```bash
bin/magento indexer:show-mode
bin/magento indexer:status
```

Two modes per indexer:

- **`realtime`** ("Update on Save") — reindex happens synchronously inside the admin save /
  import transaction. Fine for a dev box; on a real store it makes every product save slow
  and causes lock contention during imports.
- **`schedule`** ("Update by Schedule") — changes are logged to changelog tables (mview)
  and applied by cron within a minute. **This is the correct production mode for all
  indexers.**

Finding: any indexer in `realtime` on a production store → **high** severity. Fix:

```bash
bin/magento indexer:set-mode schedule    # all indexers
```

`indexer:status` interpretation:

| Status | Meaning |
|---|---|
| Ready | In sync. Good. |
| Reindex required | Invalidated; cron should pick it up — if it stays for hours, cron is broken |
| Processing (for hours) | A reindex died holding state → `indexer:reset <id>` then `indexer:reindex <id>` |
| Schedule backlog growing | mview consumer not keeping up or cron dead (next section) |

## Cron health

Magento cron must run **every minute** (the internal scheduler decides what actually
executes). Check the crontab on the server:

```bash
crontab -l -u <web-user>     # expect: * * * * * php bin/magento cron:run ...
bin/magento cron:install     # writes the standard 1-minute entry if missing
```

Then verify it's actually executing — the `cron_schedule` table is the ground truth:

```sql
-- recent activity per status; 'success' rows with recent finished_at = healthy
SELECT status, COUNT(*), MAX(finished_at) AS last
FROM cron_schedule GROUP BY status;

-- jobs that error repeatedly
SELECT job_code, COUNT(*) AS errors, MAX(messages) AS last_error
FROM cron_schedule WHERE status = 'error'
GROUP BY job_code ORDER BY errors DESC LIMIT 10;

-- jobs stuck 'running' (crashed mid-flight; blocks reruns of the same job)
SELECT job_code, executed_at FROM cron_schedule
WHERE status = 'running' AND executed_at < NOW() - INTERVAL 2 HOUR;
```

Run via CLI without DB credentials at hand:
`bin/magento db:query` doesn't exist — use `n98-magerun2 db:query` if installed, or
`mysql` with credentials from `app/etc/env.php`.

Severity guide:

- No rows in `cron_schedule` newer than ~10 minutes → **critical** (cron not running at all).
- `indexer_update_all_views` erroring or absent → **critical** (schedule-mode indexers never
  apply; the store serves stale prices/stock).
- Millions of rows in `cron_schedule` → **medium**: history cleanup not running; check
  `system/cron/*/history_cleanup_every` config and look for a job erroring before cleanup.
- Jobs stuck `running` for hours → **high**: that job group is wedged. Clear the row and
  find the crash in `var/log/cron.log` / `var/log/support_report.log`.

## Cron groups & separate processes

`crontab.xml` assigns jobs to groups (`default`, `index`, `consumers`). With the standard
single `cron:run` entry all groups share one process — one slow job (e.g. a 20-minute
sitemap generation) delays indexing. On busy stores split them:

```
* * * * * php bin/magento cron:run --group=index
* * * * * php bin/magento cron:run --group=default
```

Also check `use_separate_process` per group in env.php/admin config.

## Message-queue consumers

Async operations (bulk admin actions, async stock/price APIs, some email) run through
queue consumers, started by the `consumers` cron group when
`cron_consumers_runner.cron_run` is true in `app/etc/env.php`:

```bash
bin/magento queue:consumers:list
grep -A6 cron_consumers_runner app/etc/env.php
```

If `cron_run` is false and there's no supervisor/systemd unit running consumers → bulk
operations queue forever. **High** severity on stores using async APIs or Inventory (MSI)
reservations; otherwise note as info.

## Mview backlog check

For schedule-mode indexers, backlog = rows in `*_cl` changelog tables not yet applied:

```sql
SELECT * FROM mview_state WHERE state != 'idle' OR (mode = 'enabled');
-- version_id vs the MAX(version_id) of the matching <view_id>_cl table = backlog size
```

A consistently growing backlog with cron healthy means the indexer itself is too slow for
the change rate (common with huge catalogs + frequent imports) — consider batching imports
and reviewing third-party indexer plugins before throwing hardware at it.
