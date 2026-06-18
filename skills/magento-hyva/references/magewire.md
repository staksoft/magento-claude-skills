# Magewire — Reactive Server-Driven Components

[Magewire](https://magewire.dev) (a Magento port of Laravel Livewire) lets you build reactive
components — forms, filters, steppers, the Hyvä checkout — **without writing JavaScript**. The
component state and logic live in a PHP class; Magewire syncs the DOM over AJAX as the user
interacts. It's bundled with Hyvä via `magewirephp/magewire`.

Reach for Magewire when interactivity needs server data, validation, or persistence on each
change. Reach for plain Alpine ([alpine.md](alpine.md)) when it's purely client-side.

## Anatomy

A Magewire component = a PHP class + a `.phtml` template, wired through layout XML.

```php
// Magewire/Subscribe.php
namespace Vendor\Theme\Magewire;

use Magewire\Component;

class Subscribe extends Component
{
    public string $email = '';
    public ?string $message = null;

    protected $rules = [
        'email' => 'required|email',
    ];

    /**
     * Called when `email` changes (wire:model) — live validation.
     */
    public function updatedEmail(string $value): void
    {
        $this->validateOnly('email');
    }

    /**
     * Bound to a button via wire:click.
     */
    public function submit(): void
    {
        $this->validate();
        // ... persist the subscription via an injected service ...
        $this->message = 'Subscribed!';
        $this->email = '';
    }
}
```

Public properties are the reactive state; public methods are callable actions. Inject
dependencies through the constructor as usual (it's a normal DI class).

Template (`templates/subscribe.phtml`), wired with `wire:` directives:

```php
<div>
    <input type="email" wire:model.debounce.500ms="email"
           class="border rounded px-3 py-2">

    <button type="button" wire:click="submit"
            wire:loading.attr="disabled"
            class="btn-primary">
        <span wire:loading.remove>Subscribe</span>
        <span wire:loading>Saving…</span>
    </button>

    <template x-if="$wire.message">
        <p class="text-green-600" x-text="$wire.message"></p>
    </template>
</div>
```

Register it in layout XML as a block whose template is the component, using Magewire's
`magewire` block argument (Hyvä provides the `magewire()` view helper / block type):

```xml
<referenceContainer name="content">
    <block name="vendor.subscribe"
           template="Vendor_Theme::subscribe.phtml">
        <arguments>
            <argument name="magewire" xsi:type="object">Vendor\Theme\Magewire\Subscribe</argument>
        </arguments>
    </block>
</referenceContainer>
```

## Key directives

- `wire:model[.debounce.Nms|.lazy]` — bind an input to a public property.
- `wire:click="method"` / `wire:submit.prevent="method"` — call a component action.
- `wire:loading[.remove|.attr="disabled"|.class="opacity-50"]` — react to in-flight requests.
- `wire:poll[.Ns]` — re-render on an interval.
- `$wire` — access the component from Alpine (`x-data` can read `$wire.property`), bridging
  Magewire state into client-side Alpine.

## Gotchas

- **Only public properties survive between requests** and they're serialized to the client —
  never put secrets or huge objects in them; keep state minimal and primitive.
- Long-running work in an action blocks the response — offload to a queue
  (magento-module `cli-cron.md`) and use `wire:poll` to reflect progress.
- Validation uses Laravel-style rules (`$rules` + `validate()`); show errors via the
  component's error bag in the template.
- A component re-renders its whole template on each round-trip; keep it scoped to the
  interactive region, not the whole page.
- Full-page cache: a Magewire component's initial render is cached with the page; its
  *updates* are dynamic AJAX, so it stays FPC-safe as long as the initial state isn't
  user-specific (use customer-data/stores for per-user bits).
