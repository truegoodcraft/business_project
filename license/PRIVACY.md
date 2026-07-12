# PRIVACY.md

# BUS Core Privacy Statement

Last updated: July 12, 2026

BUS Core is designed to run locally on your machine.
Because of this architecture, operational business records remain under the operator's control.

---

## Local Operation

All operational data is stored locally in a **SQLite database** on your device.

Examples include:

* inventory records
* manufacturing recipes
* cost data
* production logs
* sales records

This data is not transmitted to the developer.

---

## Current Network Signals

Current BUS Core releases can make optional version-aware update checks. Those requests may include the current app version, release channel, and whether the local profile has previously attempted a version-aware check. They do not include an installation identifier, shop records, customer data, item or recipe data, invoice contents, quantities, financial values, file paths, or machine fingerprints.

Published v1.3.2 releases do not contain the broader product client. The current repository working revision implements it behind a first-run disclosure and settings control, and it sends nothing until that disclosure is acknowledged with telemetry enabled. It uses a random locally generated UUIDv4 installation identifier and sends only allowlisted event names with an event ID, timestamp, app version, release channel, and coarse operating-system category. It queues at most 100 events, retries at most three times, and discards unsupported older-server responses without affecting local work. Turning telemetry off clears the unsent queue.

The payload constructor cannot accept customer, supplier, employee, item, recipe, invoice, email, document, filepath, financial, quantity, raw database, username, hardware, or machine-fingerprint content. Lighthouse migration 0013 and Worker 1.22.0 must be deployed and production-verified before this client is released.

---

## No Hosted Account Required

BUS Core Self-Managed does not require a hosted account, cloud service, or subscription. A local instance can remain unclaimed, or an operator can configure local users and permissions; those local accounts do not create a TGC-hosted account.

The software can run completely offline when optional network features, including update checks, are disabled. TGC Managed BUS is an upcoming optional service in which TGC would operate an isolated deployment for the customer. It is not generally available in the current release.

---

## Local Web Interface

BUS Core runs a local web interface normally available at:

```
http://localhost:8765
```

This interface is accessible **only from your device by default**, unless you intentionally configure your system to expose it to a network.

---

## Optional Update Checks

If enabled, the software may check a public repository for new releases.

These requests do not include operational business data or a persistent client identifier.

Update checks can be disabled.

---

## Data Ownership

You control the data stored in BUS Core Self-Managed and can export it.

In the current self-managed product, TGC does not host or control your database.

Because the system runs locally, the developer cannot recover lost data.

Self-managed operators are responsible for maintaining backups. The upcoming Managed BUS service is intended to add managed backups, recovery, export, and offboarding around the same BUS Core product without creating a divergent fork.
