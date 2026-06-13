<p align="center">
  <a href="https://www.staksoft.com/">
    <img src="assets/logo.svg" alt="StakSoft — Magento &amp; Mage-OS development studio" width="280">
  </a>
</p>

# Magento 2 & Mage-OS Skills for Claude Code

**magento-claude-skills** is a free, open-source [Claude Code](https://claude.com/claude-code) plugin that gives Claude (and the Claude Agent SDK) expert, current knowledge of **Magento 2, Mage-OS, and Adobe Commerce** development. It makes the AI scaffold modules correctly, choose the right extension mechanism, and audit storefront performance — producing code that compiles with `bin/magento setup:di:compile` and passes `phpcs --standard=Magento2` on the first try.

Maintained by [StakSoft](https://www.staksoft.com/), a software studio with 10+ years of Magento and e-commerce engineering experience. Verified against **Mage-OS 3.0.0 / Magento 2.4.9 on PHP 8.3**.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Magento 2.4.x](https://img.shields.io/badge/Magento-2.4.x-orange.svg)
![Mage-OS compatible](https://img.shields.io/badge/Mage--OS-compatible-blue.svg)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2.svg)

---

## Contents

- [What you get](#what-you-get)
- [Install](#install)
- [Skill commands and how to use them](#skill-commands-and-how-to-use-them)
- [Magento CLI command reference](#magento-cli-command-reference)
- [What each skill covers](#what-each-skill-covers)
- [Why it exists](#why-it-exists)
- [Requirements](#requirements)
- [Works well with](#works-well-with)
- [FAQ](#faq)
- [Hire Magento &amp; Mage-OS developers](#hire-magento--mage-os-developers)
- [About StakSoft](#about-staksoft)
- [License](#license)

---

## What you get

Two skills that load on demand when you ask Claude a relevant question:

| Skill | What it does | Triggers on |
|---|---|---|
| **`magento-module`** | Scaffold and extend Magento modules the right way — plugin vs observer vs preference decisions, declarative schema, dependency injection, admin UI, layout XML, REST/GraphQL APIs, CLI/cron/queues, and debugging playbooks. | "create a Magento module", "observer or plugin?", "my layout XML isn't working", "setup:di:compile fails" |
| **`magento-audit`** | Performance audit of a Magento storefront — full-page cache leaks (`cacheable="false"` scanner), Varnish/Redis/`env.php` config, indexer and cron health, TTFB and Core Web Vitals. Works from a URL, a codebase, or both. | "my Magento store is slow", "audit storefront performance", "Varnish not caching", "FPC hit rate" |

In a benchmark of real module-build and debugging tasks, the `magento-module` skill scored **100% vs an 86% baseline** (no skill) on a Mage-OS 2.4.9 install — every generated module compiled and passed the Magento coding standard.

## Install

**Option 1 — `npx skills` (recommended, fastest):** the [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI installs both skills into `.claude/skills/`. No clone needed.

```bash
npx skills add staksoft/magento-claude-skills -a claude-code
```

Add `-g` for a global install (all projects), or `-y` for non-interactive/CI.

**Option 2 — Claude Code plugin marketplace:** installs the whole plugin.

```bash
claude plugin marketplace add staksoft/magento-claude-skills
claude plugin install magento-skills
```

**Option 3 — from a local clone:**

```bash
git clone https://github.com/staksoft/magento-claude-skills.git
claude plugin install ./magento-claude-skills
```

## Skill commands and how to use them

The skills trigger automatically from natural language, or you can invoke them explicitly.

| Command | Use it to | Example |
|---|---|---|
| `/magento-module <Vendor_Module>` | Scaffold a new module with correct `registration.php`, `module.xml`, and `composer.json`, then build the feature. | `/magento-module Acme_GiftMessage` |
| `/magento-module` (free text) | Add a plugin/observer, declarative-schema table, admin grid, REST/GraphQL endpoint, CLI command, or cron job. | "add a plugin that uppercases SKUs on save" |
| `/magento-audit <url>` | Audit a live storefront for full-page cache, TTFB, and Core Web Vitals issues. | `/magento-audit https://store.example/` |
| `/magento-audit <path>` | Audit a codebase for FPC killers, `env.php` cache config, and indexer/cron health. | `/magento-audit ./app/code` |

You don't have to type the command — asking *"why isn't my product page caching?"* or *"create a module that adds a gift-message field to checkout"* triggers the right skill on its own.

## Magento CLI command reference

The `magento-module` and `magento-audit` skills know which `bin/magento` commands to run and how to read their output. This is the quick reference they apply — useful for any Magento 2 / Mage-OS developer:

| Command | Purpose |
|---|---|
| `bin/magento module:enable Vendor_Module` | Enable a module after creating it. |
| `bin/magento setup:upgrade` | Register modules, apply `db_schema.xml` and data patches. |
| `bin/magento setup:di:compile` | Compile dependency injection; catches plugin and DI mistakes. |
| `bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module` | Regenerate the declarative-schema whitelist after a `db_schema.xml` change. |
| `bin/magento cache:flush` / `cache:clean layout full_page block_html` | Clear caches; targeted clean during layout development. |
| `bin/magento indexer:status` / `indexer:reindex` / `indexer:show-mode` | Check, rebuild, and inspect indexers (any `realtime` indexer in production is a finding). |
| `bin/magento setup:static-content:deploy` | Deploy static assets (required in production mode). |
| `bin/magento dev:di:info "Vendor\Class"` | Show preferences, constructor args, and every plugin on a class — essential for debugging. |
| `bin/magento dev:template-hints:enable` | Overlay block/template paths on the storefront to debug layout. |
| `bin/magento cron:install` / `cron:run --group=<group>` | Install the system crontab; run a cron group on demand. |
| `bin/magento queue:consumers:list` / `queue:consumers:start <name>` | Inspect and run message-queue consumers. |
| `bin/magento deploy:mode:show` / `deploy:mode:set developer` | Show or switch between developer and production mode. |
| `vendor/bin/phpcs --standard=Magento2 app/code/Vendor/Module` | Lint code against the official Magento 2 coding standard. |

## What each skill covers

### `magento-module` — module development

A `SKILL.md` workflow plus nine on-demand reference docs and a deterministic scaffold script:

- **extension-mechanisms** — plugin vs observer vs preference vs `di.xml` argument decision tree
- **declarative-schema** — `db_schema.xml`, the schema whitelist, EAV and extension attributes
- **di-patterns** — dependency injection, factories, proxies, virtual types, area scoping
- **admin-ui** — `system.xml` config, ACL, menus, and `ui_component` admin grids
- **frontend** — layout XML, view models, output escaping, FPC awareness, Hyvä vs Luma
- **api** — REST (`webapi.xml`) and GraphQL (schema + resolvers) over service contracts
- **cli-cron** — console commands, cron jobs and groups, message queues and consumers
- **debugging** — playbooks for `setup:di:compile` failures, layout not applying, stuck indexers
- **checklists** — a pre-finish gate covering security, caching, i18n, and coding standards
- **scripts/scaffold.py** — generates module boilerplate with no XML-namespace typos

### `magento-audit` — storefront performance

A cache-first audit workflow with five reference docs and two scripts:

- **fpc-audit** — full-page cache misses and `cacheable="false"` leaks
- **indexers-cron** — indexer modes, mview backlog, and cron health
- **frontend-perf** — Core Web Vitals, JS/CSS bundling, LCP
- **server-config** — `env.php`, Redis, Varnish, OpenSearch
- **scoring** — a severity-ranked rubric so the report leads with impact-per-effort
- **scripts/** — `check-headers.py` (parses `X-Magento-Cache-Debug`, TTFB) and `scan-layout.py` (finds FPC killers)

## Why it exists

Generic LLM output for Magento is often subtly wrong, because the public web is full of decade-old tutorials. Common mistakes these skills prevent:

- `ObjectManager::getInstance()` instead of constructor injection
- Deprecated `InstallSchema`/`UpgradeSchema` scripts instead of declarative `db_schema.xml`
- A `<preference>` class rewrite where a **plugin** would compose without conflict
- Block classes instead of view models for template logic
- Unescaped template output (an XSS finding)
- `cacheable="false"` blocks that silently disable full-page cache for an entire page

Each skill encodes current Magento 2.4.x / Mage-OS conventions **and a verification step**, so Claude hands back code that compiles and passes `phpcs --standard=Magento2` rather than plausible-looking code that breaks on `setup:di:compile`.

## Requirements

- A **Magento 2.4.x or Mage-OS** codebase. The skills verify with `bin/magento setup:di:compile` and `phpcs --standard=Magento2` when a running install is available.
- **PHP 8.1+** to run generated code; **Python 3** for the scaffold and audit scripts.
- **Claude Code** or the Claude Agent SDK.

## Works well with

These skills carry the *procedures and conventions*; for live store and merged-config access, pair them with a Magento MCP server:

- [elgentos/magento2-dev-mcp](https://github.com/elgentos/magento2-dev-mcp) — merged Magento configuration for AI agents
- [mage-os-lab/magento2-lsp](https://github.com/mage-os-lab/magento2-lsp) — Language Server + MCP for Magento code navigation

## FAQ

**Is this free?**
Yes. The plugin is open source under the MIT license. You only need Claude Code or the Claude Agent SDK.

**Does it work with Adobe Commerce and Mage-OS, or only Magento Open Source?**
All three. Magento Open Source, Adobe Commerce, and Mage-OS share the same module architecture (2.4.x), so the conventions apply identically. It was verified on Mage-OS 3.0.0 (Magento 2.4.9).

**What is a Claude skill?**
A skill is packaged expertise — instructions, reference docs, and scripts that load into Claude's context only when a relevant task appears. Unlike an MCP server, which gives Claude live *access* to a store, a skill changes how *correctly* Claude writes and debugs Magento code.

**Do I need a Magento MCP server to use it?**
No. The skills work standalone against a local codebase. An MCP server is optional and adds live merged-config and store data — see [Works well with](#works-well-with).

**Which Magento versions are supported?**
Magento 2.4.x and Mage-OS, on PHP 8.1+. The conventions target current declarative schema, dependency injection, and service-contract patterns — not deprecated Magento 2.2/2.3 approaches.

**How is this different from a Magento MCP server?**
An MCP server connects Claude to a running store's API or config. This plugin teaches Claude the *development conventions and debugging procedures* so the code it writes is correct. They are complementary — use both for the best results.

## Hire Magento & Mage-OS developers

Need expert hands on your Magento, Mage-OS, or Adobe Commerce project? StakSoft builds and maintains custom modules, headless storefronts, integrations, and performance optimizations.

- 🧩 **[Hire a Magento developer](https://www.staksoft.com/hire/magento-developer)** — custom modules, extensions, upgrades, and integrations
- ⚡ **[Hire a Mage-OS developer](https://www.staksoft.com/hire/mageos-developer)** — Mage-OS builds, migrations, and community-edition expertise
- 📬 **[Contact StakSoft](https://www.staksoft.com/contact)** — tell us about your project

## About StakSoft

[StakSoft](https://www.staksoft.com/) is a software development and product innovation studio with 10+ years of engineering experience. Specializations include **e-commerce engineering** (Magento, Mage-OS, Shopify, headless commerce, payment integrations, and performance optimization), SaaS products, mobile apps (Flutter), and cloud/DevOps. StakSoft also builds AI-powered products including Scan2PDF, Scan2Call, and PDFaiGen.

- 🌐 Website: [staksoft.com](https://www.staksoft.com/)
- 🧩 [Hire a Magento developer](https://www.staksoft.com/hire/magento-developer)
- ⚡ [Hire a Mage-OS developer](https://www.staksoft.com/hire/mageos-developer)
- 📬 [Contact us](https://www.staksoft.com/contact)

## License

MIT © [StakSoft](https://www.staksoft.com/). See [LICENSE](LICENSE).

---

<sub>Keywords: Magento 2 Claude skill, Mage-OS Claude Code plugin, Adobe Commerce AI developer tools, Magento module development AI, Magento MCP, magento-module, magento-audit, setup:di:compile, phpcs Magento2, full-page cache audit. Last updated June 2026.</sub>
