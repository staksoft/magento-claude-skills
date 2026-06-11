# Pre-Finish Checklist

Run through this before declaring any Magento module task complete. Each item is a real
review/marketplace rejection reason, not ceremony.

## Compile & standards (always)

- [ ] `bin/magento setup:upgrade` ran clean (if schema/patches changed)
- [ ] `bin/magento setup:di:compile` passes
- [ ] `vendor/bin/phpcs --standard=Magento2 app/code/Vendor/Module` clean (if phpcs +
      magento/magento-coding-standard installed; `composer require --dev magento/magento-coding-standard` to add)
- [ ] No `ObjectManager::getInstance()`, no `$_GET`/`$_POST`/superglobals, no raw SQL in
      templates or controllers
- [ ] Every class, constructor, and public method has a PHPDoc block — the Magento2 phpcs
      standard warns on missing docblocks even when types are declared natively

## Consistency

- [ ] `composer.json` name matches vendor/module (`acme/module-gift`), `registration.php`
      and `etc/module.xml` agree on `Acme_Gift`
- [ ] `etc/module.xml` `<sequence>` lists modules whose XML you extend/override (sequence
      controls XML merge order, not class loading)
- [ ] di.xml entries are in the narrowest applicable area directory
- [ ] If db_schema.xml changed: `etc/db_schema_whitelist.json` regenerated and committed

## Security

- [ ] Every `.phtml` output escaped (`escapeHtml`/`escapeHtmlAttr`/`escapeUrl`/`escapeJs`);
      `@noEscape` only with a comment justifying trust
- [ ] Admin controllers define `ADMIN_RESOURCE`; matching acl.xml entries exist
- [ ] POST endpoints implement `HttpPostActionInterface` (form-key/CSRF protected)
- [ ] User input validated/cast before use; collection filters use bound params (the
      collection API does this — just never concatenate into `getSelect()->where()`)
- [ ] Secrets in config use encrypted backend model, never logged

## Caching & performance

- [ ] No `cacheable="false"` added to shared-page layout (use customer-data sections instead)
- [ ] Models rendered on frontend implement `IdentityInterface` so FPC invalidates correctly
- [ ] No work in constructors; heavy CLI/cron deps proxied
- [ ] Collections loaded with needed columns/filters, not `load()` inside loops

## i18n

- [ ] All user-visible strings wrapped: `__('...')` in PHP/templates, `translate="label"`
      attributes in XML
- [ ] `i18n/en_US.csv` present with each phrase (`"Gift message","Gift message"`)

## Cleanup

- [ ] No commented-out code, debug logging, or `var_dump`/`Zend_Debug`
- [ ] Test/demo modules removed from `app/code` on shared installs
- [ ] `bin/magento cache:flush` as the final step so the user sees current behavior
