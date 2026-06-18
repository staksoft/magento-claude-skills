# Changelog

All notable changes to **magento-claude-skills** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] — 2026-06-13

### Added
- **`magento-hyva` skill** — Hyvä theme development: Alpine.js + Tailwind CSS components,
  Magewire reactive server-driven components, child-theme setup and the Tailwind build,
  overriding Hyvä/Luma templates and layout XML, and Luma→Hyvä compatibility. Six reference
  docs plus a `scaffold-theme.py` child-theme generator.
- **`magento-module` testing reference** — `testing.md`: PHPUnit unit + integration tests,
  the Magento ObjectManager test helper, mocking patterns, and integration fixtures.

### Changed
- `magento-module` now has ten references (added testing) and `api.md` now documents the
  verified `getList()`/SearchResults/CollectionProcessor pattern.

### Verified
- The PHPUnit unit-test pattern was written and run green on **Mage-OS 3.0.0 / Magento 2.4.9
  with PHPUnit 12** — surfacing that PHPUnit 10+ ignores docblock metadata, so data providers
  must use the PHP-attribute form `#[DataProvider(...)]` (documented in `testing.md`).
- The `magento-hyva` scaffold output was structure-verified (valid PHP, XML, JS, JSON). A live
  Hyvä render requires the licensed `hyva-themes/magento2-default-theme` package.

## [0.2.0] — 2026-06-13

### Added
- **`magento-audit` skill** — storefront performance audit (full-page cache leaks,
  `cacheable="false"` scanner, Varnish/Redis/`env.php` config, indexer & cron health,
  TTFB and Core Web Vitals) with `check-headers.py` and `scan-layout.py` scripts and a
  severity-ranked scoring rubric. Works from a URL, a codebase, or both.
- **`magento-module` references** — `api.md` (REST `webapi.xml` + GraphQL schema/resolvers
  over service contracts) and `cli-cron.md` (console commands, cron jobs/groups, message
  queues/consumers).
- **`npx skills` install path** — `npx skills add staksoft/magento-claude-skills -a claude-code`
  via the vercel-labs/skills CLI, alongside the Claude Code plugin marketplace.
- SEO/GEO-optimized README with a Magento CLI command reference, FAQ, and vendored logo.

### Changed
- Refined the `magento-module` trigger description: added concrete triggers (EAV attributes,
  totals/fees, admin grids, Mage-OS migration, composer constraints) and an explicit negative
  boundary that hands storefront-performance questions to `magento-audit`.
- Sharpened the docblock checklist item (tag-only PHPDoc blocks warn under `phpcs Magento2`;
  use a short description or `@inheritDoc`).

### Verified
- All examples compile on **Mage-OS 3.0.0 / Magento 2.4.9 / PHP 8.3** and pass
  `phpcs --standard=Magento2`. A module with a plugin, CLI command, REST route, and cron job
  was built, compiled, and exercised end to end.
- `magento-module` benchmarked at **100% vs an 86% baseline** on real build/debug tasks.

## [0.1.0] — 2026-06-12

### Added
- Initial release: **`magento-module`** skill (SKILL.md, extension-mechanisms,
  declarative-schema, di-patterns, admin-ui, frontend, debugging, checklists references,
  and a deterministic `scaffold.py`) plus a `magento-audit` stub.
- Claude Code plugin manifest and marketplace source.

[0.3.0]: https://github.com/staksoft/magento-claude-skills/releases/tag/v0.3.0
[0.2.0]: https://github.com/staksoft/magento-claude-skills/releases/tag/v0.2.0
[0.1.0]: https://github.com/staksoft/magento-claude-skills/releases/tag/v0.1.0
