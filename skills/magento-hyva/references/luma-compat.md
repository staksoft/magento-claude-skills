# Luma → Hyvä Compatibility

The hardest part of running Hyvä isn't the theme — it's the **third-party modules** that were
written for Luma. A Luma extension typically ships frontend output that assumes RequireJS,
Knockout, jQuery, and its own LESS. On a Hyvä storefront none of that loads, so the module's
frontend silently does nothing (or errors in the console).

## Why a Luma module breaks on Hyvä

- Its templates call `data-mage-init` / `text/x-magento-init` / `require([...])` → Hyvä has no
  RequireJS, so the JS never runs.
- It adds Knockout `data-bind` / UI components → no Knockout, nothing binds.
- It enqueues LESS or jQuery widgets → not present.
- It references Luma layout handles/containers that Hyvä renamed or removed.

The module's **backend** (plugins, observers, prices, data) works fine — only the *frontend
rendering* needs a Hyvä equivalent.

## The fix options, in order

1. **Use the vendor's Hyvä-compatible module if it exists.** Many popular extensions ship a
   `hyva-themes/magento2-<vendor>-<module>` compat package (community-maintained ones live in
   the Hyvä compatibility-module registry / GitLab). Install it and the frontend is provided
   for you.
2. **Use Hyvä's compat fallback.** `hyva-themes/magento2-compat-module-fallback` lets specific
   Luma modules keep rendering their RequireJS output inside Hyvä as a stopgap — heavier, but
   unblocks a launch. Register the module to fall back rather than be suppressed.
3. **Re-implement the frontend in your child theme.** For your own or a small module, copy its
   template into the theme (`app/design/frontend/Vendor/theme/Third_Module/templates/...`) and
   rewrite the interactive bits in Alpine/Magewire. The block/view-model layer is reused as-is.

Check what's available before building: search Packagist and the Hyvä compatibility registry
for the module name + "hyva".

## Converting a storefront Luma → Hyvä (the shape of the project)

1. Install the licensed Hyvä default theme; create a child theme ([theme-setup.md](theme-setup.md)).
2. Set Hyvä on a **staging store view** first, leaving Luma live.
3. Inventory third-party modules; for each, find a compat module, enable fallback, or plan a
   re-implementation. This inventory is usually the bulk of the effort.
4. Port custom theme templates: rewrite Knockout/jQuery as Alpine/Magewire, LESS as Tailwind.
5. Move customer-data/private-content usage to Hyvä's stores/Magewire mechanism so FPC stays
   intact ([alpine.md](alpine.md)).
6. Build Tailwind, deploy static content, QA every template-heavy page (PDP, PLP, cart,
   checkout), then switch the production store view.

## Detecting the problem

If a feature works on Luma but not Hyvä: open the browser console (RequireJS/Knockout errors
or simply nothing firing), and grep the module for `data-mage-init`, `x-magento-init`,
`require(`, `data-bind`, or `.less` — any hit means it needs a Hyvä frontend. The
magento-audit skill's frontend checks can also flag leftover RequireJS payloads.
