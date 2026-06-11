# Debugging Playbooks

Mechanical procedures for the classic Magento failure modes. Run them in order; each step
either fixes the issue or tells you which branch to take.

## setup:di:compile failures

The error output is long but the actual cause is in the first "error" lines. Common cases:

**"Incompatible argument type: Required type: X. Actual type: Y"**
A di.xml argument or preference binds the wrong class. Check your `etc/*/di.xml` for the
class named in the error; verify the `xsi:type` and the class exists with that exact
namespace (typos compile fine in XML and explode here).

**"Class X does not exist" (for a Factory/Proxy/Interceptor)**
Usually fine — generated classes are created during compile. If it persists:
```bash
rm -rf generated/code generated/metadata
bin/magento setup:di:compile
```
If still failing, the *base* class name is wrong somewhere (di.xml, constructor type hint,
or a `…Factory` referencing a class that doesn't exist).

**"Cannot instantiate interface X"**
Something injects interface X but no `<preference for="X" .../>` binds an implementation.
Either you forgot the preference for your own Api interface, or you injected a core
interface that's only bound in a specific area (check which area's di.xml has the binding —
`bin/magento dev:di:info "X"` shows the effective preference).

**Circular dependency**
"Circular dependency: X depends on Y and vice versa." Break it by injecting a Proxy for one
side (via di.xml, see di-patterns.md) or rethinking which class owns the logic.

**Area-specific compile errors** (mentions `\Magento\Backend` in frontend, etc.)
A class usable only in one area is injected in a global context. Move the plugin/type config
into the area-specific di.xml, or proxy the dependency.

## "My plugin/observer doesn't fire"

1. Module enabled? `bin/magento module:status Acme_Gift`
2. Caches: `bin/magento cache:clean config` (config XML is cached aggressively).
3. Right area? A plugin declared in `etc/adminhtml/di.xml` never runs on the storefront.
4. Plugin target valid? Plugins don't work on: final/private/protected methods, virtual
   types, `__construct`, objects created with `new`. Confirm the method is public and the
   object comes from the ObjectManager.
5. Verify registration: `bin/magento dev:di:info "Target\Class\Name"` lists every plugin
   with sortOrder. If yours is absent → XML problem (wrong `<type name>` — must be the class
   that *declares* the method or its interface). If present but seemingly not running →
   another `around` plugin with lower sortOrder may not be calling `$proceed()`.
6. For observers: confirm exact event name (grep core for `dispatch('event_name'`) and area
   of events.xml. Add a temporary `$this->logger->debug()` to prove execution.
7. In production mode, recompile after di.xml changes: `bin/magento setup:di:compile`.

## "My layout XML isn't applying"

1. `bin/magento cache:clean layout full_page block_html`
2. Filename must exactly match the full action name: route id + controller dir + action,
   lowercase with underscores (`acme_gift_message_index.xml`). Find the real handle by
   checking the body class on the rendered page (`<body class="... acme-gift-message-index">`).
3. Right area dir? `view/frontend/layout/` vs `view/adminhtml/layout/`.
4. Theme override winning? A file with the same name in the active theme
   (`app/design/frontend/...`) merges *after* yours and can remove/move your block.
5. Validate the XML against the schema — a silently invalid file is skipped. Check
   `var/log/system.log` for "Invalid XML" entries.
6. Block not rendering but layout fine → template path typo (`Acme_Gift::file.phtml` must
   exist under `view/frontend/templates/file.phtml`) — check `system.log` for
   "Invalid template file" warnings.
7. Last resort: enable template/block hints (Stores → Config → Advanced → Developer, or
   `bin/magento dev:template-hints:enable`) to see what's actually rendering where.

## "Works in developer mode, broken in production mode"

Production mode differences: no automatic code generation, no automatic static content, all
caches on, errors hidden.

1. Check real error: `var/log/exception.log`, `var/log/system.log`, or temporarily
   `bin/magento deploy:mode:set developer` on a staging copy.
2. Missing generated classes → you deployed without `setup:di:compile`.
3. Missing/stale assets (404 on css/js) → `setup:static-content:deploy` for every deployed
   locale/theme.
4. "Works after cache flush, breaks later" → your code varies output per user/store on a
   cached page; revisit FPC strategy (frontend.md).

## Stuck indexers / cron / mview

```bash
bin/magento indexer:status        # look for "Reindex required" or processing/backlog
bin/magento cron:install --force  # ensure crontab exists (or check cPanel/system cron)
```

1. Backlog never drains → cron not running. Check `cron_schedule` table has recent rows:
   `SELECT job_code, status, MAX(finished_at) FROM cron_schedule GROUP BY job_code, status;`
2. Indexer stuck "processing" for hours → a previous run died holding the state. Reset:
   `bin/magento indexer:reset <indexer_id> && bin/magento indexer:reindex <indexer_id>`
3. Frequent "Undefined index"/deadlocks during reindex → corrupt changelog; as a controlled
   fix, `indexer:set-mode realtime` then back to `schedule` recreates mview subscriptions.
4. Your own indexer/consumer not running → check `crontab.xml` group, and for queue
   consumers verify `bin/magento queue:consumers:list` and that a runner is configured
   (`cron_consumers_runner` in env.php).

## General triage order for "500 error / white page"

1. `var/log/exception.log` (most recent stack trace) → fix the named class.
2. `pub/static` or `generated` permission/ownership errors after deploys are the most
   common non-code cause.
3. `bin/magento maintenance:status` — someone left maintenance mode on.
4. Third-party conflict suspected → `bin/magento module:disable Suspect_Module` on staging,
   bisect.
