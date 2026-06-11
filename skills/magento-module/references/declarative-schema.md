# Declarative Schema (db_schema.xml)

Since Magento 2.3, database structure is declared in `etc/db_schema.xml` and Magento diffs
the declaration against the actual DB on `setup:upgrade`. Never write `InstallSchema`,
`UpgradeSchema`, or `InstallData` classes — they are deprecated and make schema state
impossible to audit. (Data — not structure — changes go in **data patches**, below.)

## A complete example

```xml
<?xml version="1.0"?>
<schema xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Setup/Declaration/Schema/etc/schema.xsd">
    <table name="acme_gift_message" resource="default" engine="innodb" comment="Acme Gift Messages">
        <column xsi:type="int" name="entity_id" unsigned="true" nullable="false" identity="true" comment="ID"/>
        <column xsi:type="int" name="order_id" unsigned="true" nullable="false" comment="Order ID"/>
        <column xsi:type="varchar" name="message" length="255" nullable="false" default="" comment="Message"/>
        <column xsi:type="decimal" name="fee" scale="4" precision="12" nullable="false" default="0" comment="Fee"/>
        <column xsi:type="timestamp" name="created_at" on_update="false" nullable="false" default="CURRENT_TIMESTAMP" comment="Created At"/>
        <constraint xsi:type="primary" referenceId="PRIMARY">
            <column name="entity_id"/>
        </constraint>
        <constraint xsi:type="foreign" referenceId="ACME_GIFT_MESSAGE_ORDER_ID_SALES_ORDER_ENTITY_ID"
                    table="acme_gift_message" column="order_id"
                    referenceTable="sales_order" referenceColumn="entity_id" onDelete="CASCADE"/>
        <index referenceId="ACME_GIFT_MESSAGE_ORDER_ID" indexType="btree">
            <column name="order_id"/>
        </index>
    </table>
</schema>
```

Gotchas that cost compile/upgrade cycles:
- `referenceId` for foreign keys follows the convention `TABLE_COLUMN_REFTABLE_REFCOLUMN`
  uppercased. It must be unique DB-wide.
- `xsi:type="timestamp"` needs `on_update`; `datetime` doesn't support defaults like
  CURRENT_TIMESTAMP on older MySQL — prefer timestamp for audit columns.
- Renaming a column needs `onCreate="migrateDataFrom(old_name)"` on the new column —
  otherwise Magento drops and recreates, losing data.
- **Dropping** things: declarative schema only removes what the *whitelist* says your module
  created. After any db_schema.xml change, regenerate the whitelist:

```bash
bin/magento setup:db-declaration:generate-whitelist --module-name=Acme_Gift
```

This creates `etc/db_schema_whitelist.json` — commit it. Without it, removals are ignored.

Then apply with `bin/magento setup:upgrade` and verify with
`bin/magento setup:db:status`.

## Don't add columns to core tables

Adding a column to `sales_order` or `catalog_product_entity` via db_schema.xml *works*, but
couples you to core internals and collides with other extensions. Prefer:

1. **Extension attributes** (`etc/extension_attributes.xml`) — the API-visible way to attach
   data to core entities:

```xml
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Api/etc/extension_attributes.xsd">
    <extension_attributes for="Magento\Sales\Api\Data\OrderInterface">
        <attribute code="acme_gift_message" type="string"/>
    </extension_attributes>
</config>
```

   You then persist it yourself — typically in a satellite table keyed by the entity id,
   loaded/saved via plugins on the entity's repository (`afterGet`, `afterSave`,
   `afterGetList`).

2. **EAV attributes** for products/customers/categories when admins should manage the value
   (created in a data patch with `EavSetupFactory`).

## Data patches (for data, not structure)

```php
namespace Acme\Gift\Setup\Patch\Data;

use Magento\Framework\Setup\Patch\DataPatchInterface;
use Magento\Framework\Setup\ModuleDataSetupInterface;

class AddDefaultTemplates implements DataPatchInterface
{
    public function __construct(private readonly ModuleDataSetupInterface $moduleDataSetup) {}

    public function apply(): self
    {
        $this->moduleDataSetup->getConnection()->startSetup();
        // insert rows, create EAV attributes, etc.
        $this->moduleDataSetup->getConnection()->endSetup();
        return $this;
    }

    public static function getDependencies(): array { return []; }  // other patch classes
    public function getAliases(): array { return []; }
}
```

Patches run once, in dependency order, tracked in the `patch_list` table. They are forward-
only; implement `PatchRevertableInterface` only if uninstall cleanliness matters.

## Models for your table

Standard trio — Model, ResourceModel, Collection — plus a repository if other modules will
consume it:

- `Model/GiftMessage.php` extends `\Magento\Framework\Model\AbstractModel`,
  `_construct()` calls `$this->_init(ResourceModel\GiftMessage::class);`
- `Model/ResourceModel/GiftMessage.php` extends `AbstractDb`,
  `_construct()` calls `$this->_init('acme_gift_message', 'entity_id');`
- `Model/ResourceModel/GiftMessage/Collection.php` extends `AbstractCollection`,
  `_construct()` calls `$this->_init(Model::class, ResourceModel::class);`

Expose CRUD through `Api/GiftMessageRepositoryInterface` + `Api/Data/GiftMessageInterface`
with a preference binding in di.xml — that's the service contract other code should use.
