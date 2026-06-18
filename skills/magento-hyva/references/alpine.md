# Alpine.js in Hyvä

Hyvä uses [Alpine.js](https://alpinejs.dev) for client-side interactivity — the small,
declarative replacement for Knockout/jQuery. Alpine lives in HTML attributes; there is no
separate JS file to register.

## Core directives

```html
<div x-data="{ open: false, qty: 1 }">
    <button type="button" @click="open = !open"
            :aria-expanded="open">
        Toggle
    </button>

    <div x-show="open" x-transition x-cloak>
        <input type="number" x-model.number="qty" min="1">
        <span x-text="`Total: ${qty * 10}`"></span>
    </div>
</div>
```

- `x-data` — declares a component and its reactive state (a JS object).
- `@click` / `x-on:click` — event handlers; also `@submit.prevent`, `@keydown.escape`.
- `:class` / `x-bind:class` — bind attributes, e.g. `:class="open ? 'block' : 'hidden'"`.
- `x-model` — two-way bind a form field (`.number`, `.debounce.500ms` modifiers).
- `x-show` vs `x-if` — `x-show` toggles `display`; `x-if` (on a `<template>`) adds/removes DOM.
- `x-text` / `x-html` — set content; prefer `x-text` (escapes) unless HTML is trusted.
- `x-init` — run code when the component initializes.
- `x-cloak` — hide an element until Alpine loads (Hyvä ships the `[x-cloak]{display:none}` rule).

## Passing PHP data into Alpine — escape it

State that comes from PHP must be escaped as the attribute value it is:

```php
<div x-data='<?= $escaper->escapeHtmlAttr(json_encode([
    "price" => $block->getPrice(),
    "label" => __("Add to cart")->render(),
])) ?>'>
    <span x-text="label"></span>
</div>
```

`json_encode` + `escapeHtmlAttr` is the safe, conventional way to seed an Alpine component
with server data. Never interpolate raw PHP into a JS expression.

## Sharing state — Alpine stores and events

For cross-component state (mini-cart count, customer data) Hyvä uses **Alpine stores** and
**`$dispatch`** custom events, mirroring Luma's customer-data sections:

```html
<!-- publisher -->
<button @click="$dispatch('add-to-cart', { sku: 'ABC' })">Add</button>

<!-- subscriber, anywhere on the page -->
<div x-data="{ count: 0 }" @add-to-cart.window="count++">
    Items: <span x-text="count"></span>
</div>
```

```js
// a global store (Hyvä registers private-content stores similarly)
Alpine.store('cart', { count: 0, add() { this.count++ } });
// in markup: x-data, then $store.cart.count
```

Hyvä's private/customer data (cart, logged-in state) is exposed through the `Magewire`/
`hyva` customer-data mechanism rather than Luma's `customer-data.js`; read it via the provided
stores instead of fetching it yourself, so it stays full-page-cache safe.

## CSP (Content Security Policy)

Hyvä storefronts often run Magento's CSP in **restrict** mode, which blocks inline event
handlers and inline `<script>` unless whitelisted. Alpine attributes (`@click`, `x-data`) are
allowed because they're parsed by Alpine, not the browser's inline-handler mechanism — but a
literal inline `<script>…</script>` you add needs the secure renderer:

```php
<?= /* @noEscape */ $secureRenderer->renderTag('script', [], 'window.foo = 1;', false) ?>
```

When a script "works in developer mode but is blocked in production," CSP is the usual cause —
move it through `$secureRenderer` or add a policy in `Vendor_Module::etc/csp_whitelist.xml`.

## Keep it small

The reason to use Hyvä is the tiny JS payload. If a component grows beyond a few dozen lines
of Alpine, or needs server data/validation on every change, it probably belongs in **Magewire**
([magewire.md](magewire.md)) instead of hand-written Alpine + fetch.
