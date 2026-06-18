# Overriding Templates, Blocks & Layout in Hyvä

Hyvä is still Magento under the hood: **layout XML, blocks, view models, and the template
fallback all work exactly as in Luma.** Only the template *contents* (Alpine + Tailwind instead
of Knockout + LESS) differ. So overriding follows the standard Magento rules.

## Override a template

Copy the Hyvä (or module) template into your child theme at the mirrored path:

```
# overriding the Hyvä default theme's product price template:
app/design/frontend/Vendor/theme/Magento_Catalog/templates/product/price/final_price.phtml

# overriding a module's frontend template:
app/design/frontend/Vendor/theme/Vendor_Module/templates/foo.phtml
```

Your theme's copy wins because the theme merges *after* the parent theme and modules. Find the
source you're overriding under `vendor/hyva-themes/magento2-default-theme/...` or the module's
`view/frontend/templates`, copy it, then edit — don't write from scratch.

## Add a block via layout XML

Layout XML is identical to Luma — the block class defaults to
`Magento\Framework\View\Element\Template`, logic goes in a view model:

```xml
<!-- app/design/frontend/Vendor/theme/Magento_Catalog/layout/catalog_product_view.xml -->
<page xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" layout="1column"
      xsi:noNamespaceSchemaLocation="urn:magento:framework:View/Layout/etc/page_configuration.xsd">
    <body>
        <referenceContainer name="product.info.main">
            <block name="vendor.badge" template="Vendor_Theme::product/badge.phtml">
                <arguments>
                    <argument name="view_model" xsi:type="object">Vendor\Theme\ViewModel\Badge</argument>
                </arguments>
            </block>
        </referenceContainer>
    </body>
</page>
```

Container and block names are the same as Luma (`content`, `product.info.main`, `header.panel`,
…). If a referenced container "doesn't exist," you may be targeting a Luma-only name that Hyvä
renamed — verify against the Hyvä default theme's layout, not Luma's.

## Hyvä view-model helpers

Hyvä ships view models you should reuse instead of reinventing:

- `Hyva\Theme\ViewModel\HeroiconsOutline` / `HeroiconsSolid` — inline SVG icons:
  ```php
  /** @var \Hyva\Theme\ViewModel\HeroiconsOutline $heroicons */
  $heroicons = $viewModels->require(\Hyva\Theme\ViewModel\HeroiconsOutline::class);
  echo $heroicons->cartHtml('w-6 h-6', 24, 24);
  ```
- `Hyva\Theme\ViewModel\Store`, `Hyva\Theme\ViewModel\Modal`, `Hyva\Theme\ViewModel\SvgIcons`
  for store context, accessible modals, and custom icon sets.
- `\Magento\Framework\View\Element\Block\ArgumentInterface` is still the base for your own view
  models (same as the magento-module `frontend.md` reference).

## What you do NOT do

- Don't add `requirejs-config.js`, Knockout `data-bind`, or `data-mage-init` — Hyvä doesn't
  load RequireJS/Knockout, so they're dead code.
- Don't create LESS files; style with Tailwind ([tailwind.md](tailwind.md)).
- Don't override `Magento_Theme/templates/root.phtml` or the head blocks unless you truly need
  to — Hyvä's are CSP- and performance-tuned.
