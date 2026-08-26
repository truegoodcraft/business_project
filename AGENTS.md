# BUS Core Agent Governance

This file is the mandatory starting point for humans, agents, and automation working in this repository. Read it before inspecting runtime state or modifying files.

## 1. Authority and drift handling

Use authority in this order:

1. Explicit owner instructions for the current task and its approved scope.
2. Estate-wide governance projected from `tgc-ops`, only for estate policy within that system's ownership boundary. `TGC-COMPLIANCE.md` is a local snapshot and is not edited here unless that projection is separately authorized.
3. `SOT.md` for intended BUS Core behavior, contracts, state, and operational constraints.
4. `CHANGELOG.md` for shipped and pending change history.
5. Code and tests as implementation evidence that must conform to the SOT.
6. `OPERATIONS.md` for the repeatable diagnostic procedure subordinate to the SOT.
7. `API_CONTRACT.md`, numbered maps, `README.md`, and secondary documents.

Known projection boundary: the generated local `TGC-COMPLIANCE.md` snapshot still lists only `SOT.md` and `README.md` as local authority documents. Do not edit that projection in this repository. Updating the estate-owned source and re-projecting it is a separate `tgc-ops` action requiring explicit approval; until then, report the snapshot as projection debt rather than claiming estate alignment is complete.

If these sources disagree, stop at the conflict. Report the exact files, implementation evidence, and operational consequence. Do not silently choose code, rewrite the SOT, or invent intent.

## 2. Required read order

Before BUS Core work:

1. Read this file.
2. Read `SOT.md` and the current `CHANGELOG.md` entry.
3. For analytics, update checks, Lighthouse, or incident diagnosis, read `OPERATIONS.md` in full.
4. Read the relevant contract/map document.
5. Inspect the smallest necessary code and tests.

Do not rediscover known access paths by probing every surface. Follow the checked-in procedure and report stale procedure text as drift.

## 3. Scope and approval gates

Repository reads are allowed when they are within the task. The following require explicit owner approval for the specific action or a task whose wording clearly authorizes it:

- changing files;
- reading local operator state under `%LOCALAPPDATA%\BUSCore`;
- starting, importing, restarting, or stopping BUS Core;
- calling a local HTTP endpoint;
- making an outbound request, including a Lighthouse update check or telemetry flush;
- running tests, smoke harnesses, build scripts, signing, packaging, or release checks;
- creating commits, branches, pull requests, tags, releases, or wiki updates;
- pushing, publishing containers, uploading artifacts, deploying, migrating external state, or changing secrets.

Never commit, push, create a PR, build, sign, tag, publish, deploy, migrate, or rotate secrets merely because a documentation edit was approved. A push to `main` can publish GHCR images, and wiki-path changes can publish the public wiki; both are separate external actions.

Before any approved Windows build, read `05_RELEASE_UPDATE_AND_DEPLOYMENT_FLOW.md`: the governed gate may access package indexes and run local launch smoke, its build implementation replaces existing `build/` and `dist/`, and release mode accesses the certificate provider and timestamp service. Record an explicit prior-artifact preserve/discard decision. Release-mirror publication is ordered rather than transactional, so partial external state and any reconciliation require separate owner approval.

Do not print or commit passwords, session values, recovery codes, telemetry event IDs, signing material, database contents, or other sensitive values. Prefer selected aggregate fields over whole-file dumps.

## 4. Diagnostic safety

Treat diagnostic actions by their effects, not by HTTP method or friendly label.

- Checked-in repository reads are zero-mutation.
- Direct reads of selected AppData files are zero-mutation only when the target files are read directly; they still require local-state scope.
- Calls to an already-running BUS Core instance write request-log evidence. Claimed-mode authenticated calls may also update session `last_seen_at`.
- `GET /app/update/check` is public but is not a passive probe. A performed check makes an outbound manifest request, can alter Lighthouse evidence, writes a request log, and can enqueue product telemetry. While `update_check_first_reported` remains false, each performed check also retries its best-effort persistence; after a write succeeds, later checks do not rewrite it.
- `GET /app/telemetry/status` reads local delivery state and does not flush or contact Lighthouse, but it is authenticated and request-logged.
- Starting BUS Core can initialize or migrate storage, acquire locks, index data, emit startup telemetry, and start a telemetry flush. Never launch it merely to inspect analytics.
- `POST /app/telemetry/preference`, internal telemetry flushes, and `POST /app/update/stage` are mutating operations, not diagnostics.

If necessary access is not approved or available, return `ACCESS_BLOCKED` with the missing evidence and the smallest approval needed. Do not manufacture evidence by forcing a check, flush, launch, preference save, or staging action.

## 5. Analytics and cross-service boundaries

- BUS Core owns local consent/config, event construction, pending delivery, local counters, update-manifest fetches, and update staging/handoff.
- Lighthouse owns receiver acceptance, exact acknowledgements, aggregate storage, release-manifest serving, and receiver-side rate/error evidence.
- Agent Smith consumes Lighthouse evidence and owns report formatting, WATCH/ALERT evaluation, and notification orchestration. It does not call BUS Core directly.
- `buscore-site` owns the linked public privacy/support pages. Cross-repository wording changes require an explicit synchronization review; they are not silently made from this repo.

Update-route counts and product-telemetry events are independent fact streams. Never add, substitute, or reinterpret them as people, authenticated clients, installs, adoption, engagement, retention, or per-install completeness.

The public-site `dev_mode` cookie is unrelated to the native client. `BUS_DEV=1` exposes development behavior but does not disable product telemetry, change its destination, or bypass authentication.

## 6. Change control

Before editing:

- verify the exact branch, commit, and worktree state;
- preserve unrelated owner changes;
- identify whether the work is a conformance fix, approved behavior change, or future proposal;
- confirm the complete rollback-safe file set.

For every meaningful repository change:

- update `CHANGELOG.md`;
- update `SOT.md` when behavior, contracts, authority, storage, or operations change;
- bump `INTERNAL_VERSION` in `core/version.py`;
- keep affected operator and contract documents synchronized;
- keep public `VERSION` unchanged unless the owner explicitly approves a release-version change.

Code behavior changes must include code, tests, SOT, changelog, internal version, and affected contracts in one coherent bundle. Documentation must describe implemented reality, not future behavior.

Use rollback-safe local patches. Do not delete or overwrite owner work. Do not edit `TGC-COMPLIANCE.md` or `wiki/` as part of ordinary local documentation work.

## 7. Required completion report

Every modification report must state:

- branch and baseline commit;
- files changed;
- behavior changed: Yes/No;
- `SOT.md` updated: Yes/No;
- `CHANGELOG.md` updated: Yes/No;
- version change, including public and internal values;
- validation performed and validation intentionally not performed;
- runtime, local-state, network, production, and external-system interactions;
- unresolved drift;
- blocked items requiring separate approval;
- commit/push/deploy status.

For analytics diagnosis, also report the access level, evidence side effects, delivery-proof level, time window, and which service owns each conclusion. Use the evidence template in `OPERATIONS.md`.
