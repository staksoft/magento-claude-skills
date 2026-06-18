# Testing Magento Modules (PHPUnit)

Magento ships several test types. For module development the two that matter most are **unit**
and **integration** tests; the rest (API-functional, MFTF, static, performance) are situational.

| Type | Location in a module | Speed | Touches | Use for |
|---|---|---|---|---|
| Unit | `Test/Unit/` | fast (ms) | nothing real — all deps mocked | pure logic: plugins, models, helpers, view models |
| Integration | `Test/Integration/` | slow (s) | real DB, real ObjectManager, real config | repositories, observers, end-to-end module behavior |
| API-functional | `Test/Api/` | slow | running app via web API | REST/GraphQL endpoints |

Put tests inside the module so they ship and run with it:
`app/code/Vendor/Module/Test/Unit/...` and `.../Test/Integration/...`.

## Unit tests

A unit test isolates one class and mocks every dependency. Extend
`PHPUnit\Framework\TestCase`. For classes with many constructor args, Magento's
`ObjectManager` test helper builds the subject and auto-mocks unlisted dependencies.

```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Test\Unit\Model;

use Magento\Framework\TestFramework\Unit\Helper\ObjectManager;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;
use Psr\Log\LoggerInterface;
use Vendor\Module\Model\PriceFormatter;

class PriceFormatterTest extends TestCase
{
    private PriceFormatter $formatter;
    private LoggerInterface $logger;

    protected function setUp(): void
    {
        $this->logger = $this->createMock(LoggerInterface::class);
        $objectManager = new ObjectManager($this);
        $this->formatter = $objectManager->getObject(
            PriceFormatter::class,
            ['logger' => $this->logger]
        );
    }

    public function testFormatAddsCurrencySymbol(): void
    {
        self::assertSame('$9.99', $this->formatter->format(9.99));
    }

    #[DataProvider('roundingProvider')]
    public function testFormatRounds(float $input, string $expected): void
    {
        self::assertSame($expected, $this->formatter->format($input));
    }

    public static function roundingProvider(): array
    {
        return [
            'rounds up'   => [9.995, '$10.00'],
            'rounds down' => [9.991, '$9.99'],
        ];
    }
}
```

> **PHPUnit version matters.** Magento 2.4.8+ / Mage-OS 3.0 ship **PHPUnit 10–12**, which
> **ignore docblock metadata** — use PHP 8 attributes: `#[DataProvider('method')]`,
> `#[Test]`, `#[Group('...')]` (import from `PHPUnit\Framework\Attributes\*`). The old
> `@dataProvider`/`@test` docblock annotations silently do nothing on PHPUnit 12 — a data
> provider that isn't honored shows up as `ArgumentCountError: Too few arguments`. Older
> Magento (2.4.6 and earlier, PHPUnit 9) still used the docblock form.

Mocking patterns that cover most needs:

```php
// simple mock with a stubbed return
$repo = $this->createMock(ProductRepositoryInterface::class);
$repo->method('getById')->with(42)->willReturn($productMock);

// assert a method is called exactly once with a given argument
$logger->expects(self::once())
    ->method('warning')
    ->with(self::stringContains('out of stock'));

// mock only some methods of a concrete class
$session = $this->getMockBuilder(CustomerSession::class)
    ->disableOriginalConstructor()
    ->onlyMethods(['getCustomerGroupId'])
    ->getMock();
```

Rules that keep unit tests useful:
- Test **behavior and contracts**, not private internals — assert on return values and on
  interactions with mocked collaborators.
- One logical assertion per test; name the test after the behavior (`testReturnsNullWhenDisabled`).
- Never hit the DB, filesystem, or `ObjectManager::getInstance()` in a unit test — if you
  can't avoid it, it's an integration test.
- Use `@dataProvider` for table-driven cases instead of copy-pasted tests.

Run them (PHPUnit 9–12 depending on the Magento version):

```bash
vendor/bin/phpunit -c dev/tests/unit/phpunit.xml.dist app/code/Vendor/Module/Test/Unit
```

A module can ship its own `phpunit.xml` for IDE/CI convenience, but the command above using
Magento's unit config is what runs in practice.

## Integration tests

Integration tests boot the real framework and a **dedicated test database** (configured in
`dev/tests/integration/etc/install-config-mysql.php`). They are the right tool for
repositories, observers, plugins-in-context, and anything depending on real DI/config.

```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Test\Integration\Model;

use Magento\TestFramework\Helper\Bootstrap;
use PHPUnit\Framework\TestCase;
use Vendor\Module\Api\FaqRepositoryInterface;
use Vendor\Module\Api\Data\FaqInterface;
use Vendor\Module\Api\Data\FaqInterfaceFactory;

class FaqRepositoryTest extends TestCase
{
    private FaqRepositoryInterface $repository;
    private FaqInterfaceFactory $faqFactory;

    protected function setUp(): void
    {
        $objectManager = Bootstrap::getObjectManager();   // the REAL container
        $this->repository = $objectManager->get(FaqRepositoryInterface::class);
        $this->faqFactory = $objectManager->get(FaqInterfaceFactory::class);
    }

    /**
     * @magentoDbIsolation enabled
     */
    public function testSaveAndGet(): void
    {
        /** @var FaqInterface $faq */
        $faq = $this->faqFactory->create();
        $faq->setQuestion('Why test?');
        $saved = $this->repository->save($faq);

        self::assertNotNull($saved->getId());
        self::assertSame('Why test?', $this->repository->get((int) $saved->getId())->getQuestion());
    }
}
```

Key annotations / attributes (older Magento uses `@magento...` docblock annotations; 2.4.8+
also supports PHP attributes like `#[DataFixture(...)]`):
- `@magentoDbIsolation enabled` — wrap the test in a transaction and roll back, so it leaves
  no data behind. Use it almost always.
- `@magentoDataFixture Vendor_Module::Test/Integration/_files/faqs.php` — seed data before the
  test.
- `@magentoConfigFixture current_store some/config/path value` — set a store config value for
  the duration of the test.
- `@magentoAppArea adminhtml|frontend|webapi_rest` — run in a specific area.

Run them (slow; needs the integration test DB set up once):

```bash
vendor/bin/phpunit -c dev/tests/integration/phpunit.xml.dist app/code/Vendor/Module/Test/Integration
```

## Conventions & CI

- Name test classes `<ClassUnderTest>Test` and mirror the source namespace under `Test/Unit`
  or `Test/Integration`.
- `declare(strict_types=1);` in every test file; type the properties.
- Coverage isn't the goal — cover the branches that carry business risk (pricing, stock,
  permissions, money) and the bug you just fixed (write the failing test first).
- In CI, run unit tests on every push (fast) and integration tests on a schedule or pre-merge
  (they need a DB). Magento's own `bin/magento dev:tests:run` wraps these on some versions.
- Phpcs also lints tests — give test methods docblocks or keep them self-descriptive to avoid
  warnings (see [checklists.md](checklists.md)).

## Verify

```bash
vendor/bin/phpunit -c dev/tests/unit/phpunit.xml.dist app/code/Vendor/Module/Test/Unit
# expect: OK (N tests, M assertions)
```
