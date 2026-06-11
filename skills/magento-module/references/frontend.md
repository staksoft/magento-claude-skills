# Frontend: Layout XML, Templates, View Models

## The request → page pipeline

route (`etc/frontend/routes.xml`) → controller returns a Page result → layout handles merge
(`default.xml` + `<route>_<controller>_<action>.xml` across all modules and the theme) →
blocks render templates. Most "frontend work" is layout XML + a template + a view model.

## Layout XML essentials

File location: `view/frontend/layout/<full_action_name>.xml`, e.g.
`catalog_product_view.xml` to touch the product page, `default.xml` for every page.

```xml
<?xml version="1.0"?>
<page xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" layout="1column"
      xsi:noNamespaceSchemaLocation="urn:magento:framework:View/Layout/etc/page_configuration.xsd">
    <body>
        <referenceContainer name="content">
            <block name="acme.gift.form"
                   template="Acme_Gift::gift/form.phtml">
                <arguments>
                    <argument name="view_model" xsi:type="object">Acme\Gift\ViewModel\GiftForm</argument>
                </arguments>
            </block>
        </referenceContainer>
    </body>
</page>
```

Key operations:
- `<referenceBlock name="...">` / `<referenceContainer name="...">` — modify existing
- `<move element="x" destination="y" before="-"/>`
- `<referenceBlock name="x" remove="true"/>` — remove (display="false" to merely hide)
- `<update handle="other_handle"/>` — pull in another handle

Note the block has **no `class` attribute** — it defaults to `Magento\Framework\View\Element\Template`,
which is correct because logic lives in the view model. Only write a block class when you
genuinely need block lifecycle hooks (`_prepareLayout`, caching keys).

## View models — where template logic goes

```php
namespace Acme\Gift\ViewModel;

use Magento\Framework\View\Element\Block\ArgumentInterface;

class GiftForm implements ArgumentInterface
{
    public function __construct(private readonly \Acme\Gift\Model\Config $config) {}

    public function getMaxLength(): int
    {
        return $this->config->getMaxLength();
    }
}
```

Template `view/frontend/templates/gift/form.phtml`:

```php
<?php
/** @var \Magento\Framework\View\Element\Template $block */
/** @var \Magento\Framework\Escaper $escaper */
/** @var \Acme\Gift\ViewModel\GiftForm $viewModel */
$viewModel = $block->getData('view_model');
?>
<form class="acme-gift-form" data-mage-init='{"validation": {}}'>
    <label><?= $escaper->escapeHtml(__('Gift message')) ?></label>
    <input name="gift_message"
           maxlength="<?= $escaper->escapeHtmlAttr($viewModel->getMaxLength()) ?>"/>
</form>
```

Escaping rules (XSS findings otherwise):
- text nodes → `$escaper->escapeHtml()`
- attribute values → `escapeHtmlAttr()`
- URLs → `escapeUrl()`
- inline JS values → `escapeJs()`
- Trusted HTML you generated (e.g. from a WYSIWYG field) → `/* @noEscape */` comment, used
  deliberately and rarely.

`$escaper` is available as a template variable since 2.4; do not use the deprecated
`$block->escapeHtml()`.

## Full-page cache awareness

Never set `cacheable="false"` on a block to make it "dynamic" — that flag disables FPC for
**every page where the block's handle applies**. The correct tools for per-user content:
- **customer-data sections** (knockout + `sections.xml`) for cart/customer bits
- ESI/private content blocks with Varnish
- Ajax-loaded fragments

If a block renders entity data, give the block proper cache identities (implement
`IdentityInterface` on the model) so FPC invalidates when the entity changes.

## JS: require small, prefer vanilla

For Luma-based themes, JS components are RequireJS + (optionally) Knockout via `data-mage-init`.
Register paths/mixins in `view/frontend/requirejs-config.js`. Keep it minimal — heavy KO
components are the main Luma performance complaint.

**Hyvä themes** (increasingly the community default, and common on Mage-OS) use Alpine.js +
Tailwind, no RequireJS/Knockout. If the project's theme is Hyvä:
- templates go in your module as usual but Hyvä-compatible overrides live under
  `view/frontend/templates` consumed by the Hyvä theme fallback, with Alpine `x-data`
  instead of `data-mage-init`
- a separate `hyva-themes/...` compatibility module is the convention for shipping both
- check for Hyvä first (`composer show hyva-themes/magento2-default-theme` or theme config)
  before writing Knockout code that will never run.

## Frontend routes & controllers

`etc/frontend/routes.xml` (router id `standard`), controller
`Controller/<Controller>/<Action>.php` implementing `HttpGetActionInterface` /
`HttpPostActionInterface`, returning results from `ResultFactory` (`TYPE_PAGE`, `TYPE_JSON`,
`TYPE_REDIRECT`, `TYPE_FORWARD`). Don't echo directly and don't extend the deprecated
`Magento\Framework\App\Action\Action` when an interface + injected factories suffice.

## Static content & deploy notes

After adding/changing JS, CSS, or requirejs-config: in developer mode just flush
`static_files_cache` / delete `pub/static/frontend/...` as needed; in production mode the
change requires `bin/magento setup:static-content:deploy`. Layout/template changes need
`bin/magento cache:clean layout block_html full_page`.
