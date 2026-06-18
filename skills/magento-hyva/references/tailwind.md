# Tailwind CSS in Hyvä

Hyvä styles with Tailwind utility classes compiled at build time. There is no LESS pipeline and
no `_module.less`. You write utilities in `.phtml`, and the build tree-shakes the CSS down to
only what's used.

## Where styling lives

| Need | Where |
|---|---|
| One-off styling | Tailwind utilities directly in the `.phtml` (`class="flex items-center gap-2"`) |
| A repeated component style | a class in `tailwind-source.css` using `@apply` |
| Design tokens (colors, fonts, spacing) | `theme.extend` in `tailwind.config.js` |
| A third-party CSS dependency | import it in `tailwind-source.css` |

`web/tailwind/tailwind-source.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
    .btn-primary {
        @apply inline-flex items-center px-4 py-2 rounded bg-brand text-white
               hover:bg-brand/90 focus:ring-2 focus:ring-brand/50;
    }
}
```

Use `@apply` sparingly — Tailwind's own guidance is to prefer utilities in markup and reach for
component classes only when the same long utility string repeats across many templates.

## Customizing the design

Extend (don't replace) the parent config so Hyvä's defaults survive:

```js
theme: {
    extend: {
        colors: {
            brand: { DEFAULT: '#0d6efd', dark: '#0a58ca' },
        },
        fontFamily: {
            sans: ['Inter', 'sans-serif'],
        },
        spacing: { container: '1280px' },
    },
},
```

Then use them as normal utilities: `bg-brand`, `text-brand-dark`, `font-sans`.

## The purge/content trap (most common Tailwind-in-Hyvä bug)

Tailwind only emits CSS for class names it **sees** in the files listed under `content` in
`tailwind.config.js`. Consequences:

- A `.phtml` in a module not covered by the content globs → its classes are purged → unstyled
  in production even though it looked fine before a fresh build.
- **Dynamically built class names break.** `class="text-<?= $color ?>-500"` is invisible to
  the scanner. Use complete class strings and switch between them:

  ```php
  <?php $cls = $isActive ? 'text-green-500' : 'text-gray-400'; ?>
  <span class="<?= $escaper->escapeHtmlAttr($cls) ?>">●</span>
  ```

  or a Tailwind **safelist** in the config for class names that genuinely must be computed.

When styles vanish only after `setup:static-content:deploy`, check (1) the content globs cover
the template, and (2) no class name is string-concatenated.

## Build & deploy recap

```bash
cd app/design/frontend/Vendor/theme/web/tailwind
npm run build          # dev: npm run watch
```

The build writes `web/css/styles.css`; Magento serves it via `setup:static-content:deploy` in
production or directly from the theme in developer mode. Never hand-edit `web/css/styles.css`
— it's generated and will be overwritten.
