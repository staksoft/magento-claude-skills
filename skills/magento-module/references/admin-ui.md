# Admin Configuration, Menus, ACL, and Grids

The admin pieces are mostly XML conventions. The failure mode is inconsistency between the
files — a system.xml section without matching ACL, a menu without a route — so treat the
files below as a set.

## Store configuration (system.xml)

`etc/adminhtml/system.xml` defines fields under Stores → Configuration:

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Config:etc/system_file.xsd">
    <system>
        <section id="acme_gift" translate="label" sortOrder="200" showInDefault="1" showInWebsite="1" showInStore="1">
            <label>Acme Gift Messages</label>
            <tab>sales</tab>
            <resource>Acme_Gift::config</resource>
            <group id="general" translate="label" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                <label>General</label>
                <field id="enabled" translate="label" type="select" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Enabled</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                </field>
                <field id="max_length" translate="label" type="text" sortOrder="20" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Max Message Length</label>
                    <validate>validate-digits</validate>
                    <depends><field id="enabled">1</field></depends>
                </field>
            </group>
        </section>
    </system>
</config>
```

Defaults go in `etc/config.xml`:

```xml
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Store:etc/config.xsd">
    <default>
        <acme_gift>
            <general>
                <enabled>0</enabled>
                <max_length>255</max_length>
            </general>
        </acme_gift>
    </default>
</config>
```

Read values through a dedicated config model (not scattered `scopeConfig` calls):

```php
class Config
{
    public const XML_PATH_ENABLED = 'acme_gift/general/enabled';

    public function __construct(private readonly ScopeConfigInterface $scopeConfig) {}

    public function isEnabled(?int $storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_ENABLED,
            \Magento\Store\Model\ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }
}
```

Sensitive fields (API keys): add `<backend_model>Magento\Config\Model\Config\Backend\Encrypted</backend_model>`
and declare them in `etc/adminhtml/di.xml` sensitive/environment config lists if deploy
pipelines are involved.

## ACL (etc/acl.xml)

Every admin-facing thing needs an ACL resource — config sections (the `<resource>` tag
above), controllers, and menu items all reference these ids:

```xml
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Acl/etc/acl.xsd">
    <acl>
        <resources>
            <resource id="Magento_Backend::admin">
                <resource id="Acme_Gift::gift" title="Gift Messages" sortOrder="100">
                    <resource id="Acme_Gift::manage" title="Manage Messages" sortOrder="10"/>
                    <resource id="Acme_Gift::config" title="Configuration" sortOrder="20"/>
                </resource>
            </resource>
        </resources>
    </acl>
</config>
```

## Admin routes, menu, controllers

`etc/adminhtml/routes.xml`:

```xml
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:App/etc/routes.xsd">
    <router id="admin">
        <route id="acme_gift" frontName="acme_gift">
            <module name="Acme_Gift"/>
        </route>
    </router>
</config>
```

`etc/adminhtml/menu.xml` links a menu item to action `acme_gift/message/index` and resource
`Acme_Gift::manage`.

Admin controller at `Controller/Adminhtml/Message/Index.php`:

```php
class Index extends \Magento\Backend\App\Action implements HttpGetActionInterface
{
    public const ADMIN_RESOURCE = 'Acme_Gift::manage';   // ACL enforced here

    public function execute()
    {
        $resultPage = $this->resultFactory->create(ResultFactory::TYPE_PAGE);
        $resultPage->setActiveMenu('Acme_Gift::gift');
        $resultPage->getConfig()->getTitle()->prepend(__('Gift Messages'));
        return $resultPage;
    }
}
```

POST actions must implement `HttpPostActionInterface` (form key validation is automatic in
admin; on frontend, implement `CsrfAwareActionInterface` only when you have a real reason
to customize CSRF behavior).

## Admin grids (ui_component)

Modern grids are UI components, not the old `Block\Widget\Grid`:

1. Layout `view/adminhtml/layout/acme_gift_message_index.xml` inserts
   `<uiComponent name="acme_gift_message_listing"/>`.
2. `view/adminhtml/ui_component/acme_gift_message_listing.xml` defines columns, paging,
   filters, massactions.
3. Data comes from a virtual-type data provider over your collection, registered in
   `etc/di.xml` under `Magento\Framework\View\Element\UiComponent\DataProvider\CollectionFactory`'s
   `collections` array argument.

Grids are verbose; copy the structure from a small core module (e.g. `Magento_Cms`'s
`cms_block_listing.xml`) and adapt names — that is the established practice, not a hack.

## Consistency checklist

- system.xml `<resource>` ↔ acl.xml resource id
- menu.xml `resource` ↔ acl.xml, `action` ↔ routes.xml frontName + controller path
- controller `ADMIN_RESOURCE` ↔ acl.xml
- Every label wrapped for translation; strings repeated in `i18n/en_US.csv`
