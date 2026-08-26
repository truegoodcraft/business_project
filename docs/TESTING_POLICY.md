# BUS Core Risk-Based Testing Policy

## Purpose

BUS Core uses proportional verification. After validation scope is approved under `AGENTS.md`, run the smallest check set that can catch a plausible regression from the current change, then escalate when scope or risk increases. This policy selects scope; it does not itself authorize tests, runtime launch, network access, builds, signing, or publication. Do not run the full suite or build an executable merely by habit.

This policy governs local development and agent verification. Release gates remain mandatory at the release boundary.

## Risk levels

| Level | Trigger | Required verification |
| --- | --- | --- |
| T0 — documentation | Only prose, comments, screenshots, or non-runtime assets change. | Review the diff. Run `scripts/governance-check.ps1` when governed authority/version documents change. No pytest or build is required unless a document-truth test covers the edited claim. |
| T1 — localized | At most three runtime files change within one component, no critical boundary is touched, and behavior has a narrow regression target. | Run the directly affected test file(s) plus the new/changed regression test. For this telemetry header change: `python -m unittest tests.telemetry.test_client` (or the equivalent pytest target). |
| T2 — cross-component | Four to ten runtime files change, more than one component is involved, a shared contract changes, or no focused test can contain the risk. | Run all affected component/API test directories, relevant shared contract tests, and governance checks. Add integration tests when data crosses filesystem, database, or service boundaries. |
| T3 — critical/release | More than ten runtime files change; a migration, auth/permission, inventory or finance authority, backup/restore, update trust, path/security boundary, dependency, build/release workflow, or public version changes; or a release candidate is being prepared. | Run the full pytest suite and governance checks. Add Bandit/dependency audit for security or dependency changes. Run isolated source smoke for critical business-flow or release candidates. Build/package/sign and frozen-executable launch smoke only for build/release changes or a release candidate. |

Critical-boundary rules override file counts. A one-line permission, migration, signature, update-trust, path-validation, or money/inventory-authority change is T3.

## Selection rules

1. Start with the behavior that changed, not the total repository test count.
2. Prefer one focused regression test that proves the defect and the fix.
3. Expand to the owning component when shared helpers, schemas, routes, or persistence are involved.
4. Expand to the full suite only at T3, when targeted tests expose broader breakage, or when test ownership is unclear.
5. A failed test is never bypassed by choosing a lower level. Fix it or document why it is unrelated.
6. Test markers are advisory until every test file is classified. Path-specific targets are the authority during that cleanup.

## Check ownership and duplication

| Check | What it proves | When to run |
| --- | --- | --- |
| Focused unit/API test | The changed behavior and regression contract. | T1 and above. |
| Affected component/integration suite | Interactions inside the impacted domain. | T2 and above. |
| Full pytest | Repository-wide Python regression confidence. | T3 and release candidates. |
| Governance guard | Version mirrors and change traceability. | Meaningful control changes; always in CI. |
| Security audit | Static Python security findings and dependency advisories. | Security/dependency/source changes in CI; explicitly for T3 security work. |
| Isolated source smoke | End-to-end business flows against a disposable runtime. | Relevant T3 changes and release candidates. |
| Frozen-executable launch smoke | The packaged onefile executable actually starts and serves the UI. | Build/release changes and release candidates only. |
| Signing/ZIP verification | Publisher identity and public artifact structure. | Release mode only. |

The source smoke and frozen-executable smoke must not be combined: they diagnose different failure classes. They are intentionally kept out of routine T1/T2 edits.

## Current cleanup decisions

- Keep active `.github/workflows/ci.yml` as the canonical locked Linux/Windows full-suite gate with bounded Linux fuzz coverage. The obsolete `.github/workflows/build-test.yml` remains removed.
- Keep `.github/workflows/governance-guard.yml` active on every push/pull request because it is quick and enforces repository traceability.
- Keep `.github/workflows/security-audit.yml` on broad push/pull-request triggers until required-check and branch-protection behavior is explicitly verified; path filtering must not strand a required check in a pending state.
- Proportional local test selection does not weaken or bypass the active CI gates.
- Do not use marker-only selection as a compliance gate while classification remains incomplete. Classify files incrementally when they are touched instead of relying on a brittle snapshot count.

## Release threshold

A public release candidate requires all of the following to pass in the intended Python/build environment:

1. focused tests added for the release's fixes;
2. `scripts/release-check.ps1 -Release`, which aggregates the clean locked environment, compilation, full pytest, governance, isolated source smoke, signed build, frozen-executable launch, signature, archive, and ZIP assertions; and
3. the separately owner-controlled publication checks.

Keep the evidence summary in the release notes. Ordinary change notes need only record the selected risk level and commands actually run.
