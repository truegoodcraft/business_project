# Troubleshooting and FAQ

## Why do I need a product before a recipe?

A recipe must point to an existing Output Product. Create the inventory item, mark **This is a product**, save it, then create the recipe.

## Why did manufacturing fail with a shortage?

At least one recipe input did not have enough available stock. Read the need, have, and missing quantities, then stock in the input, reduce the run, or correct the recipe. A failed shortage run does not partially consume inputs or create output.

## Why does sale price matter?

For Stock Out reason **Sold**, price supplies sales revenue used by Finance. The product's usual price is a starting point, not a locked price. BUS Core warns when the entered price is lower.

## Is BUS Core a POS?

No. It can record product stock-out and related sale value, but it is not a full checkout, payment-processing, receipt, or register system.

## Is it accounting software?

No. Finance provides operational sales, returns, COGS, expense, and profit visibility. It is not full double-entry accounting, bank reconciliation, payroll, or tax software.

## Where is my data?

Packaged Windows production data is under `%LOCALAPPDATA%\BUSCore\app\app.db`; demo data uses `app_demo.db`. Docker normally uses `/data/app.db`, which must be persistently mounted. See [Backup and Restore](Backups-and-Data-Persistence.md).

## Does BUS Core use cloud sync or telemetry?

BUS Core has no forced cloud or cloud synchronization. BUS Core v1.3.3 can make optional version-aware update checks and includes an optional disclosed product client with a Settings opt-out, strict allowlists, bounded retries, fail-open behavior, and no business-content fields. Lighthouse 1.22.1 and migration 0013 are live and production-verified.

## Does it require an account?

No hosted account is required. BUS Core can operate in unclaimed local mode; an operator can also claim an instance and configure local users and permissions.

## Can True Good Craft manage BUS Core for me?

TGC Managed BUS is the upcoming paid operating option for customers who want TGC to host and manage an isolated BUS Core deployment, including updates, backups, monitoring, recovery, and bounded support. It uses the same BUS Core foundation rather than a divergent application, but it is not generally available yet.

## Can multiple users use it?

Local user accounts and permissions exist, but the default packaged and Docker deployments are loopback-only and are not a supported general multi-user network service. Do not expose BUS Core to a LAN or the internet based only on the presence of user accounts.

## Can I use QuickBooks or Wave?

BUS Core has no direct QuickBooks/Wave sync. Finance CSV export can support a separate manual bookkeeping process.

## Why can I not mark this stock-out as Sold?

Sold stock-out is currently supported for count items. For non-count items, use the accurate loss/theft/other reason, or model a count-based sale product when that reflects the real workflow.

## Is BUS Core frozen?

No. Core remains a maintained manufacturing operations product. After v1.3.2, work continues to prioritize reliability, security, data safety, release hygiene, documentation, tester blockers, and manufacturing workflows supported by real operating evidence.

## Is Docker supported?

The Docker image and default Compose configuration exist, but Docker/Synology guidance remains community-tested. Keep the default loopback binding and persist `/data`. See [Docker Install](Docker-Install.md).

## Where do I report a problem?

Use [Bug Reports](Bug-Reports.md). Include the BUS Core version, install method, what you attempted, what happened, and whether demo or real-shop data was active.
