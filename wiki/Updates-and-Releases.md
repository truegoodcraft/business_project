# Updates and Releases

## Version Basics

Public BUS Core releases use semantic versions such as `1.3.2`. The app's current build/version is visible in its system and update surfaces. Release notes live in the repository under `docs/releases` and on the project's release page.

## Checking for Updates

BUS Core can show a one-time startup update notice when checks are enabled. In Settings, **Check now** performs a manual read-only check. Update-check failure does not prevent normal local operation.

When a newer release is available, selecting **Update** starts manual staging. Staging verifies trusted release metadata and the downloaded Windows artifact before marking it ready. It does not overwrite the running executable or force an immediate restart. A verified staged version is considered on the next start according to launcher policy.

There is no silent background auto-install. Read-only update discovery and trusted update staging have different verification boundaries; see [Trust, Security, and Local-First](Trust-Security-and-Local-First.md).

## v1.3.2 and Core Stability

v1.3.2 is the community polish release. BUS Core remains maintained as manufacturing operations software. Future changes continue to prioritize bug fixes, data safety, backup/restore, security and trust, tester blockers, release/update reliability, documentation, operator clarity, and evidence-backed manufacturing improvements.

Core remains a complete open-source product that can be run locally or self-hosted without a subscription. The upcoming Managed BUS direction adds optional TGC operation around the same product rather than creating a divergent fork.

## Before Updating

1. Read the release notes.
2. Create an encrypted backup export and confirm it appears in the list.
3. Keep the backup password available.
4. After updating, confirm the version and run a small read/write check appropriate for your shop.
