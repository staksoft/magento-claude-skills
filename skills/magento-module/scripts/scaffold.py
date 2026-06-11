#!/usr/bin/env python3
"""Scaffold Magento 2 / Mage-OS module boilerplate.

Generates the three files every module needs — registration.php, etc/module.xml,
composer.json — with consistent naming, so the LLM/developer can focus on the parts
that need judgment (di.xml, schema, plugins, layout).

Usage:
    python scaffold.py Vendor_Module [--path app/code] [--description "..."]
                       [--sequence Magento_Catalog,Magento_Checkout]
                       [--setup-version 1.0.0]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def kebab(name: str) -> str:
    """CamelCase -> kebab-case (GiftMessage -> gift-message)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="Module name in Vendor_Module form, e.g. Acme_GiftMessage")
    parser.add_argument("--path", default="app/code", help="Base code path (default: app/code)")
    parser.add_argument("--description", default=None, help="composer.json description")
    parser.add_argument("--sequence", default="", help="Comma-separated module names this module's XML must load after")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    m = re.fullmatch(r"([A-Z][A-Za-z0-9]*)_([A-Z][A-Za-z0-9]*)", args.module)
    if not m:
        print(f"error: '{args.module}' is not a valid module name (expected Vendor_Module, CamelCase)", file=sys.stderr)
        return 1
    vendor, module = m.group(1), m.group(2)
    full_name = f"{vendor}_{module}"
    composer_name = f"{kebab(vendor)}/module-{kebab(module)}"
    description = args.description or f"{vendor} {module} module for Magento 2 / Mage-OS"
    sequence = [s.strip() for s in args.sequence.split(",") if s.strip()]

    base = Path(args.path) / vendor / module
    files: dict[Path, str] = {}

    files[base / "registration.php"] = f"""<?php
declare(strict_types=1);

use Magento\\Framework\\Component\\ComponentRegistrar;

ComponentRegistrar::register(
    ComponentRegistrar::MODULE,
    '{full_name}',
    __DIR__
);
"""

    sequence_xml = ""
    if sequence:
        deps = "\n".join(f'            <module name="{s}"/>' for s in sequence)
        sequence_xml = f"\n        <sequence>\n{deps}\n        </sequence>"
    files[base / "etc" / "module.xml"] = f"""<?xml version=\"1.0\"?>
<config xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
        xsi:noNamespaceSchemaLocation=\"urn:magento:framework:Module/etc/module.xsd\">
    <module name=\"{full_name}\">{sequence_xml}
    </module>
</config>
"""

    composer_requires = ['        "php": "~8.1.0||~8.2.0||~8.3.0"',
                         '        "magento/framework": "*"']
    for s in sequence:
        pkg_vendor, pkg_module = s.split("_", 1)
        composer_requires.append(f'        "{kebab(pkg_vendor)}/module-{kebab(pkg_module)}": "*"')
    requires = ",\n".join(composer_requires)
    files[base / "composer.json"] = f"""{{
    "name": "{composer_name}",
    "description": "{description}",
    "type": "magento2-module",
    "license": "proprietary",
    "version": "1.0.0",
    "require": {{
{requires}
    }},
    "autoload": {{
        "files": ["registration.php"],
        "psr-4": {{
            "{vendor}\\\\{module}\\\\": ""
        }}
    }}
}}
"""

    for path, content in files.items():
        if path.exists() and not args.force:
            print(f"skip (exists): {path}", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"created: {path}")

    print(f"\nNext steps:")
    print(f"  bin/magento module:enable {full_name}")
    print(f"  bin/magento setup:upgrade && bin/magento setup:di:compile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
