# CLI Commands, Cron Jobs, and Message Queues

Three ways to run code outside a web request. They share a theme: register the entry point in
XML/di.xml, keep the class thin, and push real work into an injected service.

## Console commands (bin/magento)

A command is a Symfony Console command registered through di.xml's `CommandList`:

`etc/di.xml`:

```xml
<type name="Magento\Framework\Console\CommandList">
    <arguments>
        <argument name="commands" xsi:type="array">
            <item name="acme_gift_sync" xsi:type="object">Acme\Gift\Console\Command\SyncCommand</item>
        </argument>
    </arguments>
</type>
```

`Console/Command/SyncCommand.php`:

```php
namespace Acme\Gift\Console\Command;

use Magento\Framework\Console\Cli;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;

class SyncCommand extends Command
{
    public function __construct(
        private readonly \Acme\Gift\Model\SyncService $syncService,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->setName('acme:gift:sync')
            ->setDescription('Sync gift messages to the external service')
            ->addArgument('store', InputArgument::OPTIONAL, 'Store code')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Report without writing');
        parent::configure();
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        try {
            $count = $this->syncService->run(
                $input->getArgument('store'),
                (bool) $input->getOption('dry-run')
            );
            $output->writeln("<info>Synced {$count} messages.</info>");
            return Cli::RETURN_SUCCESS;   // 0
        } catch (\Throwable $e) {
            $output->writeln("<error>{$e->getMessage()}</error>");
            return Cli::RETURN_FAILURE;   // 1
        }
    }
}
```

Things that matter:
- **Every command is constructed on every `bin/magento` call**, so a heavy constructor
  dependency slows the entire CLI. Inject expensive services via a **`\Proxy`** (set in
  di.xml) so they're only built when the command actually runs. See
  [di-patterns.md](di-patterns.md).
- Return `Cli::RETURN_SUCCESS`/`RETURN_FAILURE` (ints) — exit codes matter for cron and CI.
- Commands run in the `Magento\Framework\App\Area::AREA_GLOBAL` area by default; if your code
  needs a specific area (e.g. emulating a store for email/price rendering), use
  `Magento\Store\Model\App\Emulation` explicitly.
- Keep `execute()` orchestration-only; the business logic belongs in the injected service so
  it's reusable from cron/queue too.

## Cron jobs

`etc/crontab.xml`:

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Cron:etc/crontab.xsd">
    <group id="default">
        <job name="acme_gift_sync" instance="Acme\Gift\Cron\Sync" method="execute">
            <schedule>*/15 * * * *</schedule>
        </job>
    </group>
    <group id="acme_gift">
        <job name="acme_gift_purge" instance="Acme\Gift\Cron\Purge" method="execute">
            <config_path>acme_gift/cron/purge_schedule</config_path>  <!-- admin-configurable -->
        </job>
    </group>
</config>
```

```php
namespace Acme\Gift\Cron;

class Sync
{
    public function __construct(
        private readonly \Acme\Gift\Model\SyncService $syncService,
        private readonly \Psr\Log\LoggerInterface $logger,
    ) {
    }

    public function execute(): void
    {
        try {
            $this->syncService->run();
        } catch (\Throwable $e) {
            // a cron job MUST swallow its own exceptions or it can stall the whole group
            $this->logger->error('Acme gift sync failed: ' . $e->getMessage());
        }
    }
}
```

Cron realities:
- Nothing runs unless the system cron calls `bin/magento cron:run` (every minute) — Magento's
  scheduler then fires due jobs. On a fresh install: `bin/magento cron:install`.
- `<schedule>` is a literal cron expression; `<config_path>` instead points to a
  `system.xml` field so admins can change timing without a deploy. Use one or the other.
- Custom **groups** get their own settings (`cron/<group>/schedule_generate_every`, etc.) and
  can run in a separate process — useful to isolate a slow job from `default`.
- An unhandled exception in one job can block others in the group; always try/catch and log.
- Debug with the `cron_schedule` table: rows in `pending`/`running`/`success`/`error` tell
  you whether the job is even being scheduled. See [debugging.md](debugging.md).

## Message queues (async work)

For work that shouldn't block a request or a single cron tick (bulk exports, webhook fan-out),
publish to a queue. Magento runs RabbitMQ in production and a DB-backed queue otherwise.

Minimal wiring (four XML files in `etc/`):

```xml
<!-- communication.xml — the topic and its handler interface -->
<topic name="acme.gift.export" request="Acme\Gift\Api\Data\GiftMessageInterface"/>

<!-- queue_topology.xml — bind topic to an exchange -->
<!-- queue_publisher.xml — how the topic is published (amqp/db) -->
<!-- queue_consumer.xml — the consumer that processes messages -->
<consumer name="acmeGiftExport" queue="acme.gift.export"
          consumerInstance="Magento\Framework\MessageQueue\Consumer"
          handler="Acme\Gift\Model\ExportHandler::process"/>
```

Run consumers with `bin/magento queue:consumers:start acmeGiftExport` (one-shot, or supervised
via `cron_consumers_runner` in `env.php`, or systemd/supervisor in production).
`bin/magento queue:consumers:list` shows what's registered. For high-volume jobs prefer the
**bulk/async API** + operations over hand-rolled loops.

Publish from anywhere via `Magento\Framework\MessageQueue\PublisherInterface::publish('acme.gift.export', $dto)`.

## Verify

```bash
bin/magento setup:upgrade && bin/magento setup:di:compile
bin/magento acme:gift:sync --dry-run        # command shows up + runs
bin/magento cron:run --group=acme_gift      # job fires; check cron_schedule
bin/magento queue:consumers:list            # consumer registered
```
