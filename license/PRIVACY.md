# PRIVACY.md

# BUS Core Privacy Statement

Last updated: July 10, 2026

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

A broader limited product-telemetry system is approved for future development but is not shipped in the current release. Before it ships, it must use a versioned allowlist, provide clear first-run disclosure and settings control, allow easy opt-out, fail without affecting local work, and reject business-content fields.

---

## No Accounts

BUS Core does not require:

* user accounts
* logins
* cloud services

The software can run completely offline.

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

You own the data stored in BUS Core.

The developer does not host or control your database.

Because the system runs locally, the developer cannot recover lost data.

Users are responsible for maintaining backups.
