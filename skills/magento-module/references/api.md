# REST and GraphQL APIs

Magento exposes custom functionality through two API surfaces. Both are built on **service
contracts** (`Api/` interfaces) — never expose a Model or ResourceModel directly. Design the
interface first, bind it in di.xml, then layer REST and/or GraphQL on top.

## Service contracts first

```php
// Api/Data/GiftMessageInterface.php — the data contract (DTO)
namespace Acme\Gift\Api\Data;

interface GiftMessageInterface
{
    public const MESSAGE = 'message';

    public function getId(): ?int;
    public function getMessage(): string;
    public function setMessage(string $message): self;
}
```

```php
// Api/GiftMessageRepositoryInterface.php — the service contract
namespace Acme\Gift\Api;

use Acme\Gift\Api\Data\GiftMessageInterface;

interface GiftMessageRepositoryInterface
{
    public function get(int $id): GiftMessageInterface;
    public function save(GiftMessageInterface $giftMessage): GiftMessageInterface;
    public function deleteById(int $id): bool;
}
```

Bind implementations in `etc/di.xml`:

```xml
<preference for="Acme\Gift\Api\GiftMessageRepositoryInterface" type="Acme\Gift\Model\GiftMessageRepository"/>
<preference for="Acme\Gift\Api\Data\GiftMessageInterface" type="Acme\Gift\Model\Data\GiftMessage"/>
```

Why interfaces: the webapi and GraphQL layers, extension attributes, and other modules all
consume the *contract*. Magento auto-generates REST request/response handling from the
interface's type hints and DocBlocks, so **type every parameter and return**, and annotate
array returns (`@return \Acme\Gift\Api\Data\GiftMessageInterface[]`) — the framework reads
these to (de)serialize.

## REST (and SOAP) — etc/webapi.xml

```xml
<?xml version="1.0"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Webapi:etc/webapi.xsd">
    <route url="/V1/acme-gift/:id" method="GET">
        <service class="Acme\Gift\Api\GiftMessageRepositoryInterface" method="get"/>
        <resources>
            <resource ref="Acme_Gift::manage"/>
        </resources>
    </route>
    <route url="/V1/acme-gift" method="POST">
        <service class="Acme\Gift\Api\GiftMessageRepositoryInterface" method="save"/>
        <resources>
            <resource ref="Acme_Gift::manage"/>
        </resources>
    </route>
    <route url="/V1/acme-gift/me" method="GET">
        <service class="Acme\Gift\Api\GiftMessageRepositoryInterface" method="getForCurrentCustomer"/>
        <resources>
            <resource ref="self"/>   <!-- authenticated customer, %customer_id% injected -->
        </resources>
    </route>
</routes>
```

Rules that trip people up:
- `<resources>` is the **ACL/auth gate**, not optional. `ref="anonymous"` = public,
  `ref="self"` = logged-in customer (with `%customer_id%` substituted into a matching method
  param), or an admin ACL id for admin-token/integration access.
- The URL `:id` placeholder must match the service method's parameter name exactly.
- Method params come from the URL path, query string, or JSON body; the framework maps them
  by name. The response is serialized from the return type — which is why the return must be
  an interface, a scalar, or an array of interfaces, never a bare Model.
- No controller, no JSON encoding by hand. If you find yourself writing `json_encode` in a
  webapi handler, you've bypassed the framework.

Auth is via bearer tokens (`/V1/integration/admin/token`, `/V1/integration/customer/token`)
or an integration's OAuth — you don't implement it, you just declare the right `<resource>`.

## GraphQL

GraphQL is a separate schema + resolver layer (it does **not** read webapi.xml).

`etc/schema.graphqls`:

```graphql
type Query {
    acmeGiftMessage(id: Int!): GiftMessage
        @resolver(class: "Acme\\Gift\\Model\\Resolver\\GiftMessage")
        @doc(description: "Fetch a gift message by id")
}

type GiftMessage {
    id: Int
    message: String
}

# extend a core type instead of editing it:
type Mutation {
    setGiftMessageOnCart(input: SetGiftMessageInput!): SetGiftMessageOutput
        @resolver(class: "Acme\\Gift\\Model\\Resolver\\SetGiftMessage")
}
```

Resolver:

```php
namespace Acme\Gift\Model\Resolver;

use Magento\Framework\GraphQl\Config\Element\Field;
use Magento\Framework\GraphQl\Query\ResolverInterface;
use Magento\Framework\GraphQl\Schema\Type\ResolveInfo;
use Magento\Framework\GraphQl\Exception\GraphQlInputException;

class GiftMessage implements ResolverInterface
{
    public function __construct(
        private readonly \Acme\Gift\Api\GiftMessageRepositoryInterface $repository
    ) {
    }

    public function resolve(Field $field, $context, ResolveInfo $info, ?array $value = null, ?array $args = null)
    {
        if (empty($args['id'])) {
            throw new GraphQlInputException(__('"id" is required'));
        }
        $model = $this->repository->get((int) $args['id']);
        return ['id' => $model->getId(), 'message' => $model->getMessage()];
    }
}
```

GraphQL specifics:
- A resolver returns a **plain array** matching the type's fields (or a value forwarded to
  child resolvers), not a DTO.
- Throw the GraphQL exception types (`GraphQlInputException`,
  `GraphQlAuthorizationException`, `GraphQlNoSuchEntityException`) — generic exceptions leak
  as 500s instead of proper GraphQL errors.
- Authenticated queries: read `$context->getUserId()` / `getExtensionAttributes()->getIsCustomer()`;
  mark fields needing login. There is no webapi.xml-style `<resource>` — auth is enforced in
  the resolver or via `@doc`/context checks.
- To add fields to a **core** type (e.g. `ProductInterface`), declare the same `type ... { }`
  block with only your new field + its `@resolver` — schemas merge across modules.
- Use **DataLoader/batch resolvers** (`BatchResolverInterface`) for list fields to avoid the
  N+1 query problem on collections.

## Verify

```bash
bin/magento setup:upgrade && bin/magento setup:di:compile
bin/magento cache:flush
# REST: token then call
# GraphQL: POST to /graphql with the query; check the GraphQL schema regenerated
```

If a new REST route 404s or a GraphQL field is "cannot be queried", it's almost always a
missing `setup:upgrade`/cache flush, or a typo between the schema/webapi declaration and the
service method/resolver class.
