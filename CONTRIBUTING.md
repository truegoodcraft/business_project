# Contributing

## Governance first

1. Read `AGENTS.md`.
2. Read `SOT.md` and the current `CHANGELOG.md` entry.
3. Read `OPERATIONS.md` before analytics, update, or runtime diagnosis.
4. Verify the exact branch, commit, and worktree state; preserve unrelated owner changes.
5. Classify the work as a conformance fix, an approved behavior change, or a future proposal.

Do not silently resolve SOT/code conflicts. Report the evidence and stop until intent is approved.

## Change bundle

Every meaningful repository change must update `CHANGELOG.md` and bump `INTERNAL_VERSION` in `core/version.py`. Update `SOT.md` and affected contracts/maps whenever behavior, authority, storage, security, API, or operational meaning changes. Public `VERSION` is owner-controlled.

Behavior changes require implementation, focused tests, SOT, changelog, internal version, and affected operator/contract docs in one reviewable bundle. Documentation must not describe proposed behavior as shipped.

## Validation

Use the risk-based policy in [`docs/TESTING_POLICY.md`](docs/TESTING_POLICY.md) to select proportional tests after validation scope is approved. Ordinary local work should run the smallest checks that directly exercise the changed behavior; critical boundaries and release candidates escalate to the full chain. This local selection policy does not reduce the complete cross-platform gate run by active GitHub CI.

Behavior changes require focused regression coverage. `scripts\governance-check.ps1` is the convenience wrapper for the two static validators below and falls back to an available `python` when the repository `.venv` launcher exists but cannot run.

The static governance checks are:

```powershell
python scripts\validate_version_governance.py
python scripts\validate_change_trace.py
```

The governed Windows release-readiness gate is `scripts\release-check.ps1`. It creates a clean dependency environment, may contact configured package indexes, and runs compilation, tests, governance, isolated local launch smoke, and build work. Its build implementation recursively replaces existing repository `build/` and `dist/`, so record their state and obtain an explicit preserve/discard decision first. The gate is mutating, can be lengthy, and is not a read-only diagnostic. Run it only when that validation/build scope is approved. Its release/signing mode requires separate explicit owner approval and accesses the Windows certificate provider plus configured timestamp service.

Use `scripts\smoke.ps1` or `scripts\smoke_isolated.ps1` only when the requested test scope calls for them. There is no canonical `buscore-smoke.ps1`.

Record commands, results, skipped gates, and environmental blockers. Do not claim a gate passed when it was not run.

## External actions

No contribution request implicitly authorizes a commit, push, PR, tag, build/sign, release-mirror dispatch, wiki publication, container publication, deployment, migration, or secret operation. These require explicit owner approval. A push to `main` publishes GHCR images, qualifying wiki-path changes publish the public wiki, and release-mirror dispatch uploads R2 content before later manifest signing/verification and stable-manifest overwrite. Release publication is not atomic; cleanup or reconciliation after partial failure requires separate approval.

Completion reports must use the fields required by `AGENTS.md`.
