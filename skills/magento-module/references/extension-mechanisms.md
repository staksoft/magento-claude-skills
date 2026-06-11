# Choosing an Extension Mechanism

Magento offers four ways to change core behavior. Picking the wrong one is the #1 source of
module conflicts. Work down this decision tree and stop at the first match.

## Decision tree

1. **Does a dedicated extension point exist?** (event, extension attribute, di.xml argument,
   queue consumer, layout handle) → use it. Always cheapest to maintain.
2. **Need to react to something happening, without changing its result?** → **Observer**.
3. **Need to modify input/output of a *public* method?** → **Plugin** (interceptor).
4. **Need to change protected/private internals?** → First ask if the design can change
   (often a plugin on a different, public method achieves the goal). If truly not →
   **Preference** as a last resort, extending the original class and overriding the minimum.

## Plugins (interceptors)

Declared in `etc/di.xml` (area-scoped where possible):

```xml
<type name="Magento\Checkout\Model\Cart">
    <plugin name="acme_gift_on_add" type="Acme\Gift\Plugin\AddGiftToCart" sortOrder="10"/>
</type>
```

```php
class AddGiftToCart
{
    // before: alter arguments. Return array of new args, or null to keep them.
    public function beforeAddProduct(Cart $subject, Product $product, $requestInfo = null)
    {
        return [$product, $requestInfo];
    }

    // after: alter the result. Receives $result first, then original args.
    public function afterGetItemsCount(Cart $subject, int $result): int
    {
        return $result;
    }

    // around: full control. AVOID unless you must short-circuit — an around plugin
    // that forgets to call $proceed() silently disables every lower-sortOrder plugin.
    public function aroundSave(Cart $subject, callable $proceed)
    {
        return $proceed();
    }
}
```

Rules that prevent real bugs:
- Plugins only intercept **public** methods on classes resolved through the ObjectManager.
  They do NOT work on: final classes/methods, private/protected methods, virtual types,
  objects created with `new`, or `__construct`.
- Prefer `after` > `before` > `around`. `around` plugins stack callables and are the main
  cause of "works alone, breaks with extension X installed".
- Plugin on an **interface** intercepts all implementations — usually what you want for
  service contracts (`ProductRepositoryInterface::save`).
- `sortOrder`: lower runs first for `before`, last for `after`. Conflicts between two
  modules' plugins are resolved by sortOrder — check with `bin/magento dev:di:info "Class\Name"`.

## Observers

Declared in `etc/events.xml` (or `etc/frontend/events.xml` etc. for area scoping):

```xml
<event name="sales_order_place_after">
    <observer name="acme_notify_warehouse" instance="Acme\Gift\Observer\NotifyWarehouse"/>
</event>
```

```php
class NotifyWarehouse implements \Magento\Framework\Event\ObserverInterface
{
    public function execute(\Magento\Framework\Event\Observer $observer): void
    {
        $order = $observer->getEvent()->getOrder();
        // react; do not assume you can change what already happened
    }
}
```

- Observers are fire-and-forget: good for side effects (emails, logs, queue messages),
  wrong for altering the result of the operation (use a plugin for that).
- Find event names by grepping the core for `->dispatch('` or checking devdocs; common ones:
  `sales_order_place_after`, `checkout_cart_product_add_after`,
  `catalog_product_save_before/after`, `customer_register_success`.
- For heavy work in an observer, publish to a message queue instead of doing it inline —
  observers run synchronously inside the request.

## Preferences (class rewrites)

```xml
<preference for="Magento\Catalog\Model\Product" type="Acme\Gift\Model\Product"/>
```

Only one preference per class wins globally — two modules rewriting the same class is an
unresolvable conflict (last `sequence` wins, the other silently loses). Legitimate uses:
- Binding your implementation to **your own** interface (this is the normal DI use, not a rewrite).
- Replacing a class that has no extension points, as a documented last resort.

If you must extend a core class, override the minimum number of methods and call `parent::`.

## di.xml argument injection — the underrated option

Often the "core class" behavior you want to change is actually a constructor argument:

```xml
<type name="Magento\Catalog\Model\Product\Visibility">
    <arguments>
        <argument name="someHandlers" xsi:type="array">
            <item name="acme" xsi:type="object">Acme\Gift\Handler\Custom</item>
        </argument>
    </arguments>
</type>
```

Core classes frequently take arrays of strategies/handlers/validators — adding an item via
di.xml composes perfectly with other modules. Check the constructor before reaching for a
plugin.

## Quick reference

| Need | Mechanism |
|---|---|
| Side effect when X happens | Observer |
| Change args into a public method | before plugin |
| Change result of a public method | after plugin |
| Conditionally skip an operation | around plugin (sparingly) |
| Add a strategy/handler/validator to a list | di.xml argument |
| Bind implementation to your own interface | preference (normal DI) |
| Replace core class wholesale | preference (last resort, document why) |
