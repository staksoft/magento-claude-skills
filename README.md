# Magento 2 / Mage-OS Skills for Claude Code

A Claude Code plugin that gives Claude deep, current Magento 2 / Mage-OS expertise:

| Skill | What it does |
|---|---|
| `magento-module` | Scaffold and extend Magento modules the right way — plugin vs observer vs preference decisions, declarative schema, DI patterns, layout XML, plus debugging playbooks for DI compile errors, layout issues, and stuck indexers. |
| `magento-audit` | Performance audit of a Magento storefront — full-page cache leaks (`cacheable="false"` scanner), Varnish/Redis/env.php config, indexer & cron health, TTFB and Core Web Vitals. Works from a URL, a codebase, or both; outputs a severity-ranked report with exact fixes. |

## Why

Generic LLM output for Magento is often subtly wrong: ObjectManager abuse, `InstallSchema` scripts that have been deprecated for years, preferences where a plugin belongs, `cacheable="false"` blocks that silently kill full-page cache. These skills encode current (Magento 2.4.x / Mage-OS) conventions and verification steps so Claude generates code that compiles, passes `phpcs --standard=Magento2`, and follows community best practice.

## Install

```bash
claude plugin marketplace add staksoft/magento-claude-skills
claude plugin install magento-skills
```

Or from a local clone: `claude plugin install /path/to/magento-claude-skills`

Then in any Magento project, just ask naturally ("create a module that adds a gift-message field") or invoke directly:

```
/magento-module Acme_GiftMessage
/magento-audit https://store.example/
```

## Works well with

These skills carry the *procedures*; for live store/config access pair them with an MCP server:

- [elgentos/magento2-dev-mcp](https://github.com/elgentos/magento2-dev-mcp) — merged Magento configuration
- [mage-os-lab/magento2-lsp](https://github.com/mage-os-lab/magento2-lsp) — LSP + MCP for code navigation

## Requirements

- A Magento 2.4.x or Mage-OS codebase (skills verify with `bin/magento setup:di:compile` and `phpcs --standard=Magento2` when available)
- PHP 8.1+ for running generated code; Python 3 for the scaffold script

## About StakSoft

This plugin is maintained by [StakSoft](https://www.staksoft.com/) — a software development and product innovation studio with 10+ years of engineering experience, specializing in e-commerce engineering (Magento, Mage-OS, Shopify, headless commerce, payment integrations and performance optimization), SaaS products, mobile apps, and cloud/DevOps.

Need expert hands on your Magento or Mage-OS project?

- [Hire a Magento developer](https://www.staksoft.com/hire/magento-developer)
- [Hire a Mage-OS developer](https://www.staksoft.com/hire/mageos-developer)
- [Contact StakSoft](https://www.staksoft.com/contact)

## License

MIT
