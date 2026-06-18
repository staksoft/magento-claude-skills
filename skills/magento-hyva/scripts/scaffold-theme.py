#!/usr/bin/env python3
"""Scaffold a Hyvä child theme skeleton for Magento 2 / Mage-OS.

Generates the deterministic boilerplate — registration.php, theme.xml, and the
web/tailwind/ build directory (tailwind.config.js, postcss.config.js, package.json,
tailwind-source.css) — so the developer can focus on templates and styling.

Usage:
    python scaffold-theme.py "Vendor/theme-name" [--parent Hyva/default]
                             [--path app/design/frontend] [--title "Vendor Theme"]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theme", help='Theme id as "Vendor/theme-name", e.g. "Acme/storefront"')
    parser.add_argument("--parent", default="Hyva/default", help="Parent theme (default: Hyva/default)")
    parser.add_argument("--path", default="app/design/frontend", help="Base theme path")
    parser.add_argument("--title", default=None, help="Human-readable theme title")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    m = re.fullmatch(r"([A-Za-z0-9]+)/([A-Za-z0-9_-]+)", args.theme)
    if not m:
        print(f'error: "{args.theme}" is not a valid theme id (expected "Vendor/theme-name")', file=sys.stderr)
        return 1
    vendor, name = m.group(1), m.group(2)
    title = args.title or f"{vendor} {name}"
    base = Path(args.path) / vendor / name
    # depth from web/tailwind/ back to the Magento root (app/design/frontend/V/n/web/tailwind)
    up = "../" * (len(Path(args.path).parts) + 4)

    files: dict[Path, str] = {}

    files[base / "registration.php"] = f"""<?php
use Magento\\Framework\\Component\\ComponentRegistrar;

ComponentRegistrar::register(
    ComponentRegistrar::THEME,
    'frontend/{vendor}/{name}',
    __DIR__
);
"""

    files[base / "theme.xml"] = f"""<?xml version=\"1.0\"?>
<theme xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
       xsi:noNamespaceSchemaLocation=\"urn:magento:framework:Config/etc/theme.xsd\">
    <title>{title}</title>
    <parent>{args.parent}</parent>
</theme>
"""

    files[base / "web" / "tailwind" / "tailwind.config.js"] = f"""const config = require('@hyva-themes/hyva-modules').hyvaModules(
  require('{up}vendor/hyva-themes/magento2-default-theme/web/tailwind/tailwind.config.js')
);

module.exports = {{
  ...config,
  content: [
    '../../**/*.phtml',
    '../../**/*.html',
    '{up}app/code/**/view/frontend/**/*.phtml',
    '{up}vendor/hyva-themes/**/templates/**/*.phtml',
  ],
  theme: {{
    ...config.theme,
    extend: {{
      ...(config.theme && config.theme.extend),
      colors: {{
        brand: {{ DEFAULT: '#0d6efd', dark: '#0a58ca' }},
      }},
    }},
  }},
}};
"""

    files[base / "web" / "tailwind" / "postcss.config.js"] = """module.exports = {
  plugins: {
    'postcss-import': {},
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

    files[base / "web" / "tailwind" / "package.json"] = f"""{{
  "name": "{vendor.lower()}-{name.lower()}-tailwind",
  "version": "1.0.0",
  "private": true,
  "scripts": {{
    "build": "tailwindcss -i ./tailwind-source.css -o ../css/styles.css --minify",
    "watch": "tailwindcss -i ./tailwind-source.css -o ../css/styles.css --watch"
  }},
  "devDependencies": {{
    "@hyva-themes/hyva-modules": "^1.0",
    "autoprefixer": "^10.4",
    "postcss": "^8.4",
    "postcss-import": "^16.0",
    "tailwindcss": "^3.4"
  }}
}}
"""

    files[base / "web" / "tailwind" / "tailwind-source.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
    .btn-primary {
        @apply inline-flex items-center px-4 py-2 rounded bg-brand text-white
               hover:bg-brand/90 focus:outline-none focus:ring-2 focus:ring-brand/50;
    }
}
"""

    for path, content in files.items():
        if path.exists() and not args.force:
            print(f"skip (exists): {path}", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"created: {path}")

    print("\nNext steps:")
    print("  bin/magento setup:upgrade")
    print(f"  cd {base / 'web' / 'tailwind'} && npm ci && npm run build")
    print("  Activate the theme: Admin > Content > Design > Configuration (or config:set design/theme/theme_id)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
