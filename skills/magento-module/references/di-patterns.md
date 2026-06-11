# Dependency Injection Patterns

Magento's DI container (the ObjectManager) wires everything from merged `di.xml` files.
Your code never touches the ObjectManager directly — constructor injection only.

## Area scoping — where to put di.xml

| File | Applies to |
|---|---|
| `etc/di.xml` | everywhere (global) |
| `etc/frontend/di.xml` | storefront requests |
| `etc/adminhtml/di.xml` | admin panel |
| `etc/webapi_rest/di.xml` | REST API |
| `etc/graphql/di.xml` | GraphQL |
| `etc/crontab/di.xml` | cron runs |

Scope plugins and preferences to the narrowest area that needs them. A logging plugin on
`ProductRepository` registered globally also runs on every cron and API call — that's how
"my admin grid got slow" bugs are born.

## Constructor injection

```php
class GiftLabelProvider
{
    public function __construct(
        private readonly \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig,
        private readonly \Psr\Log\LoggerInterface $logger,
    ) {}
}
```

- Inject **interfaces**, not concrete classes, whenever an interface exists.
- Never inject session, registry, or `RequestInterface` into models — those belong in the
  presentation layer (controllers, view models).
- `__construct` cannot be intercepted by plugins; keep it assignment-only (no work, no I/O).

## Factories — when you need a *new* instance

DI gives you shared singletons. For entities you create per-use (a new model, a new
collection), inject the generated factory:

```php
public function __construct(
    private readonly \Acme\Gift\Model\GiftMessageFactory $giftMessageFactory,
) {}

public function create(): GiftMessage
{
    return $this->giftMessageFactory->create();   // or ->create(['data' => [...]])
}
```

Factories are code-generated — don't write `GiftMessageFactory` yourself; reference it and
`setup:di:compile` (or runtime generation in developer mode) creates it in `generated/`.
Same applies to `…Factory` for any class and to extension attribute classes.

## Proxies — break expensive constructor chains

If a dependency is heavy (opens DB connections, loads config) but only used on some code
paths, inject a proxy via di.xml — never hardcode the `\Proxy` class name in PHP:

```xml
<type name="Acme\Gift\Console\Command\SyncCommand">
    <arguments>
        <argument name="syncService" xsi:type="object">Acme\Gift\Model\SyncService\Proxy</argument>
    </arguments>
</type>
```

CLI commands are the classic case: every `bin/magento` invocation constructs *all* commands,
so any command with heavy constructor deps slows every CLI call — proxy them.

## Virtual types — configure without subclassing

A virtual type is a named variant of a class with different constructor args, existing only
in di.xml:

```xml
<virtualType name="AcmeGiftLogger" type="Magento\Framework\Logger\Monolog">
    <arguments>
        <argument name="handlers" xsi:type="array">
            <item name="file" xsi:type="object">AcmeGiftLogHandler</item>
        </argument>
    </arguments>
</virtualType>
<virtualType name="AcmeGiftLogHandler" type="Magento\Framework\Logger\Handler\Base">
    <arguments>
        <argument name="fileName" xsi:type="string">/var/log/acme_gift.log</argument>
    </arguments>
</virtualType>
<type name="Acme\Gift\Model\SyncService">
    <arguments>
        <argument name="logger" xsi:type="object">AcmeGiftLogger</argument>
    </arguments>
</type>
```

This custom-logger pattern is the canonical example. Remember: plugins cannot target virtual
types — they intercept the real class underneath.

## Argument types cheat sheet

```xml
<argument name="x" xsi:type="string">literal</argument>
<argument name="x" xsi:type="boolean">true</argument>
<argument name="x" xsi:type="number">42</argument>
<argument name="x" xsi:type="const">Acme\Gift\Model\Config::XML_PATH_ENABLED</argument>
<argument name="x" xsi:type="object">Acme\Gift\Model\Thing</argument>          <!-- shared -->
<argument name="x" xsi:type="object" shared="false">Acme\Gift\Model\Thing</argument>
<argument name="x" xsi:type="init_parameter">Magento\Framework\App\State::PARAM_MODE</argument>
<argument name="x" xsi:type="array">
    <item name="key" xsi:type="string">value</item>
</argument>
<argument name="x" xsi:type="null"/>
```

Array arguments **merge** across modules' di.xml files (same item name overrides by module
sequence) — that's why "add an item to a core array argument" is such a clean extension point.

## Inspecting the wiring

- `bin/magento dev:di:info "Magento\Catalog\Api\ProductRepositoryInterface"` — shows the
  preference, constructor args, and every plugin with sortOrder. Use this before adding a
  plugin to see what else is attached.
- Generated code lives in `generated/`; if stale classes cause weirdness after refactors,
  delete `generated/code` and `generated/metadata`, then recompile.
