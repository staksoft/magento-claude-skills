# Server & env.php Configuration

What `app/etc/env.php` and the surrounding stack should look like on a production Magento
2 / Mage-OS store. In codebase mode, read env.php directly (it's PHP returning an array;
never paste secrets into the report — refer to keys, not values).

## Deploy mode

```bash
bin/magento deploy:mode:show
```

`developer` or `default` mode on a live store → **critical**. Developer mode disables
caches and generates code on the fly; `default` is nearly as bad. Production stores run
`production` mode, with `setup:di:compile` + `setup:static-content:deploy` in the deploy
pipeline.

## Cache backends (env.php `cache` section)

Healthy production shape:

```php
'cache' => [
    'frontend' => [
        'default'    => ['backend' => '...\Redis', 'backend_options' => ['database' => '0', ...]],
        'page_cache' => ['backend' => '...\Redis', 'backend_options' => ['database' => '1', ...]],
    ],
],
```

Findings:

- **No `cache` section at all** → caches go to `var/cache` on disk → **high** on any store
  with real traffic (slow, and breaks on multi-server setups). Fix:
  `bin/magento setup:config:set --cache-backend=redis --cache-backend-redis-db=0`
  and `--page-cache=redis --page-cache-redis-db=1`.
- **Same Redis database number** for default cache, page cache, and sessions → **medium**:
  a `cache:flush` then wipes sessions too (logs every customer out). Separate DBs (or
  separate instances) per concern: 0 = default, 1 = page_cache, 2 = sessions is the
  conventional split.
- `compress_data`/`compress_tags` absent: defaults are fine; only flag if Redis memory is
  the known constraint.
- L2 cache (`'cache' => ['frontend' => [...], 'type' => ...]` with `remote_backend`):
  relevant only on multi-webnode setups; absence is not a finding on single-node.

## Sessions (env.php `session` section)

- `'save' => 'files'` on a busy or multi-server store → **high**: file locking serializes
  concurrent AJAX requests from the same customer (slow checkout) and breaks horizontal
  scaling. Move to Redis: `bin/magento setup:config:set --session-save=redis ...`.
- Redis sessions: check `disable_locking` (0 is the safe default; 1 trades correctness for
  speed — note it, don't auto-flag), and `max_concurrency` ≥ 6 for checkout-heavy stores.

## Varnish wiring

When `system/full_page_cache/caching_application` = 2:

- `http_cache_hosts` must be set in env.php so cache purges reach Varnish:
  ```php
  'http_cache_hosts' => [['host' => '127.0.0.1', 'port' => '6081']],
  ```
  Missing → **critical**: content updates never purge; the store serves stale pages until
  TTL expiry. (`bin/magento setup:config:set --http-cache-hosts=...`)
- VCL should originate from `bin/magento varnish:vcl:generate` for the matching Varnish
  version, then be customized — hand-rolled VCL that drops the `PURGE`/`BAN` handling or
  the `X-Magento-Vary` logic breaks invalidation or cache correctness.
- TLS: Varnish doesn't terminate TLS; expect nginx/hitch in front. Chain =
  nginx (TLS) → Varnish → nginx/php-fpm backend.

## Search engine

```bash
bin/magento config:show catalog/search/engine
```

2.4+ requires OpenSearch/Elasticsearch. Audit points: heap sized ~50% of available RAM for
the ES node (capped ~31 GB), and catalogsearch_fulltext indexer in schedule mode. Slow
category pages with layered navigation usually trace to search engine load, not MySQL.

## PHP

- **OPcache** is the single biggest PHP lever:
  `php -i | grep -E 'opcache.enable|opcache.memory|opcache.max_accelerated'`.
  Production targets: `opcache.enable=1`, `memory_consumption >= 512`,
  `max_accelerated_files >= 60000` (Magento has ~50k files), `validate_timestamps=0` on
  immutable deploys (with a deploy-time reset). Missing/undersized OPcache → **high**.
- `realpath_cache_size >= 10M`, `realpath_cache_ttl` high — cheap win, often forgotten.
- PHP-FPM `pm.max_children` sized to RAM / avg worker size; too low = request queueing
  that looks like "random slowness" under load.
- PHP version: 8.2/8.3 for current 2.4.7+/Mage-OS — each major PHP bump has been a real
  perf win; flag EOL PHP versions as high (security) regardless of perf.

## MySQL / MariaDB

Light-touch audit (deep DB tuning is out of scope):

- `innodb_buffer_pool_size` should hold the working set (rule of thumb: ~70% of a dedicated
  DB server's RAM). Default 128M on a production store → **high**.
- Slow query log enabled with long_query_time ~1s for evidence gathering.
- Flat tables (`catalog/frontend/flat_catalog_*`): legacy, removed in newer versions —
  flag as cleanup if enabled.

## What NOT to recommend

- Don't recommend `validate_timestamps=0` without a deploy process that restarts/reset
  OPcache — it causes "deploy did nothing" incidents.
- Don't recommend raising every limit "to be safe" — tie each recommendation to an
  observed symptom or a measured gap from the targets above.
- Don't touch `MAGE_MODE` env vars vs env.php without checking which one the host actually
  uses (the env var overrides env.php).
