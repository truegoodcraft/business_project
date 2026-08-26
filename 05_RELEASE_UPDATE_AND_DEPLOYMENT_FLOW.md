# 05_RELEASE_UPDATE_AND_DEPLOYMENT_FLOW

- Document purpose: Fast operational reference for version authority, build outputs, release flow, update-check behavior, and deployment assumptions, with emphasis on trustworthy infrastructure and explicit release authority.
- Primary authority basis: `core/version.py`, `scripts/validate_version_governance.py`, `scripts/validate_change_trace.py`, `scripts/build_core.ps1`, `scripts/release-check.ps1`, `BUS-Core.spec`, `core/api/routes/update.py`, `core/services/update.py`, `.github/workflows/governance-guard.yml`, `.github/workflows/release-mirror.yml`, `.github/workflows/publish-image.yml`, `.github/workflows/publish-wiki.yml`.
- Best use: Validate what is actually implemented for shipping and update checks, and separate that from older docs or tooling assumptions.
- Refresh triggers: Version bumps, build script changes, manifest URL changes, update-service changes, CI/workflow changes, signing or artifact-validation changes.
- Highest-risk drift areas: docs overstating release signing or artifact verification, treating ordered external publication as atomic/rollback-safe, hiding destructive build-output replacement, any future bypass of `.github/workflows/governance-guard.yml`, and any future split between release tags and `core/version.py`.
- Key dependent files / modules: `core/version.py`, `scripts/build_core.ps1`, `scripts/release-check.ps1`, `BUS-Core.spec`, `core/config/manager.py`, `core/api/routes/update.py`, `core/services/update.py`, `.github/workflows/release-mirror.yml`.

## Version and Update Authority Matrix

In the current stabilization phase, trustworthy release infrastructure means operators can tell where version truth lives, what the app validates, and what it does not. Update checks are default-on / opt-out for a one-shot startup notice, manual checks remain available, and the app must stay honest about the limits of current verification.

| Concern | Implemented authority | Doc / tooling assumption | Status | Notes |
| --- | --- | --- | --- | --- |
| Runtime version | `core/version.py` | FastAPI app version, build script read from same source | Canonical | `VERSION` is the owner-controlled public/release SemVer source. |
| Internal working version | `core/version.py` | Internal reports may expose `INTERNAL_VERSION` | Canonical | `INTERNAL_VERSION` is `X.Y.Z.R`, for repo working revisions only, and must not flow into strict SemVer consumers. |
| Package metadata version | `pyproject.toml` | Packaging stub only | Checked mirror | `scripts/validate_version_governance.py` now fails if `pyproject.toml` diverges from canonical `core/version.py::VERSION`. |
| Version-governance mirrors | `scripts/validate_version_governance.py` + `.github/workflows/governance-guard.yml` | `SOT.md`, Windows version metadata, package metadata | Canonical guard | Canonical version mirrors are now machine-checked on push, pull request, and manual workflow runs. |
| Security audit workflow | `.github/workflows/security-audit.yml` | Python/fuzz source and locked dependency evidence | Canonical guard | Bandit Medium/High findings fail CI; hash-locked Linux/Windows runtime, test, and fuzz dependency audits are blocking. |
| Release tag boundary | Release-triggered `.github/workflows/release-mirror.yml` checks `tag == v{VERSION}` and release tag target == default-branch commit; manual dispatch is a historical-backfill exception | GitHub release tags | Canonical boundary | Release-triggered publication enforces both checks. An explicitly owner-approved manual dispatch instead validates a requested existing tag as strict `vX.Y.Z` and intentionally skips those release-trigger checks. |
| Published manifest `latest.version` | Release-triggered runs read `core/version.py`; manual backfills parse the requested tag | Hosted manifest consumers | Canonical with explicit exception | New release publication uses canonical `VERSION`. Manual historical backfill derives `latest.version` from the requested tag so current default-branch tooling can mirror an older release. |
| Published manifest signature | `.github/workflows/release-mirror.yml` runs `scripts/sign_manifest.py` | GitHub Actions release workflow | Canonical | Generated `stable.json` is signed into `stable.signed.json`; a missing `BUSCORE_MANIFEST_SIGNING_PRIVATE_KEY` fails before manifest upload, although the versioned R2 release asset may already have been uploaded. |
| Manifest public-key trust policy | `core/runtime/manifest_keys.py` | Core runtime verifier and release workflow verification step | Canonical | Production public key `bus-core-prod-ed25519-2026-04-25` is pinned in Core; private key must never be committed. |
| Update-check route contract | `core/api/routes/update.py` | UI Settings/update notice consumes this response | Canonical public exception | Six normalized release fields plus `check_source`, `check_performed`, and nullable `skip_reason`; exact GET has no auth/permission dependency. |
| Update manifest URL | `%LOCALAPPDATA%\BUSCore\config.json` `updates.manifest_url` | `SOT.md` | Canonical | Code and docs use the Lighthouse endpoint. |
| Manifest `download_url` | `core/services/update.py` extracts and returns it | Compatibility field for check response | Canonical | `/app/update/check` is non-staging discovery with evidence side effects; guarded artifact work uses manual `/app/update/stage`. |
| Staging manifest authenticity | `core/api/routes/update.py` + `core/services/update.py` + `core/runtime/manifest_trust.py` | Manual update staging | Canonical | `/app/update/stage` requires a signed manifest from an active pinned public key before artifact download/extract/EXE trust verification. |
| Manifest checksum / hash | `core/services/update_artifact.py` plus `core/runtime/update_cache.py` | Internal update cache helper | Canonical for staging | Internal download helper requires manifest-declared `sha256`, enforces `size_bytes` when present, verifies the cached ZIP bytes, and records `hash_verified` only after the staging path has selected a trusted signed manifest. |
| Safe extraction stage | `core/services/update_extract.py` plus `core/runtime/update_cache.py` | Guarded manual staging | Canonical staging step | Safely unpacks `hash_verified` ZIPs into `updates\versions\<version>\`, requires exactly one EXE candidate, and records `extracted` only. |
| EXE Authenticode / publisher verification | `core/services/update_exe_trust.py` plus `core/runtime/update_cache.py` | Guarded manual staging | Canonical staging step | Verifies Windows Authenticode validity, True Good Craft signer-subject identity, and the pinned signer thumbprint `55474AA9A2D562022A6590D487045E069457F985`, then records `exe_verified` only. |
| Local update cache/state lifecycle | `core/runtime/update_cache.py` / update state model | Manual staging and next-start handoff | Canonical | `%LOCALAPPDATA%\BUSCore\updates\` holds `manifests\`, `downloads\`, `versions\`, and `state.json`; live conservative stages include `hash_verified`, `extracted`, `exe_verified`, the version+sha keyed current write authority `verified_ready_versions`, and legacy compatibility/latest `verified_ready`, which remains a valid read/handoff fallback. |
| DB/app ownership lock | Launcher preflight plus app-level lock | Current verified handoff prerequisite | Canonical | Same DB/app root cannot have two live BUS Core owners; handoff evaluation occurs after lock acquisition. |
| Manifest channel selection | `core/config/update_policy.py` + `core/services/update.py` | Configured channel decides selected release entry | Canonical | Non-stable channels require explicit channel-specific entries and must not fall back to public latest. |

## Build and package outputs

| Output | Status | Produced by | Destination |
| --- | --- | --- | --- |
| Windows one-file EXE | Canonical | `scripts/build_core.ps1` + `BUS-Core.spec` | `dist/BUS-Core.exe`, copied to `dist/BUS-Core-<VERSION>.exe` |
| Local structural ZIP bundle | Secondary, not a signed public candidate | `scripts/build_core.ps1 -Bundle` | `dist/BUS-Core-<VERSION>.zip`; can be structurally checked but is not the governed signed release path |
| Canonical signed public release candidate (ZIP) | Canonical | `scripts/build_core.ps1 -Release`, then separately approved external publication | `dist/BUS-Core-<VERSION>.zip`; release mode signs/verifies before bundling, while publication remains outside the build script |
| Windows version metadata file | Canonical | `scripts/build_core.ps1` | `scripts/_win_version_info.txt` |
| Bundled UI/license assets | Canonical | `BUS-Core.spec` | Embedded in PyInstaller artifact |
| Docker image | Canonical | `Dockerfile`, `.github/workflows/publish-image.yml` | GHCR tags `latest` and `:<sha>` |
| Container runtime | Canonical | `docker-compose.yml` | Publishes `127.0.0.1:8765:8765` by default, persists `/data/app.db` |

## Observed Release Flow

1. `core/version.py` is the canonical public version source; runtime and build surfaces read strict SemVer `VERSION`.
2. `v1.2.0` is superseded by `v1.2.1` because the published Windows artifact was unsigned; do not mutate or reuse the `v1.2.0` release/tag/artifact for the corrected release.
3. The `v1.2.1` Windows EXE must be Authenticode-signed before packaging/uploading, and the update path must continue rejecting unsigned artifacts such as the `v1.2.0` artifact that failed with status `NotSigned`.
4. `scripts/build_core.ps1` reads `VERSION` from `core/version.py` unless an explicit override is passed, validates `X.Y.Z`, installs the governed build graph when needed, recursively replaces existing repository `build/` and `dist/` only after environment validation, writes Windows version metadata, builds the one-file EXE, and copies `dist/BUS-Core.exe` to `dist/BUS-Core-<VERSION>.exe`. An approved build must decide whether prior outputs need preservation before execution.
5. Without `-Sign`, `-Bundle`, or `-Release`, the script remains the normal build path and stops after the versioned EXE copy.
6. `scripts/build_core.ps1 -Release` now performs the local release build boundary: it builds the versioned EXE, accesses the Windows certificate provider, contacts the configured timestamp service while signing, signs only `dist/BUS-Core-<VERSION>.exe`, verifies Authenticode validity and the signer thumbprint `55474AA9A2D562022A6590D487045E069457F985`, optionally verifies through `signtool`, and bundles `dist/BUS-Core-<VERSION>.zip`.
7. The release ZIP is created from a clean staging folder and contains only the signed versioned EXE, `README.md`, and `license/` at the ZIP root. Packaging copies the canonical root `SOT.md` to `license/SOT.md` and verifies that exact archive entry, avoiding a divergent source-tree copy.
8. The script does not store or automate signing passwords/PINs; any required credential entry remains in the Windows certificate-provider / `signtool` prompt flow.
9. GitHub release creation, Lighthouse/R2 mirroring, manifest signing, and manifest publication remain outside `scripts/build_core.ps1`.
10. `scripts/release-check.ps1` is the governed clean Windows gate: it creates a Python 3.11 environment, may contact configured package indexes while installing hash-locked runtime/test graphs, runs compile/tests/governance/isolated local launch smoke, and performs an unsigned build by default or the certificate/timestamp-using signed bundle path only with its separately approved release option.
11. `.github/workflows/release-mirror.yml` separates tooling checkout from release identity: release-triggered runs check out the published tag, while manual `workflow_dispatch` uses the repository default branch as current tooling and independently mirrors canonical input `release_tag` or deprecated compatibility input `tag` when `release_tag` is absent.
12. For published releases, the workflow fetches full history and fails unless the release tag resolves to the checked-out commit and the current default-branch commit. This prevents publishing a release tag from an older commit after the version bump or release-hygiene commits were left behind.
13. For published releases, the workflow still reads `VERSION` from `core/version.py` and fails unless the release tag exactly equals `v{VERSION}`. For manual backfills, it resolves canonical `release_tag` first and deprecated `tag` only as fallback, validates the resolved value as strict `vX.Y.Z`, derives manifest `latest.version` and expected asset name from it, and uses the same tag for release download and release-notes URL generation.
14. The same workflow downloads the exact `BUS-Core-<VERSION>.zip` release asset, computes `sha256`, uploads the asset to R2 `releases/<asset-name>`, and generates manifest `latest.version` plus an authoritative absolute `latest.download.url` using `https://lighthouse.buscore.ca/releases/BUS-Core-<VERSION>.zip`.
15. Before signing, the workflow now prints the working directory, lists `scripts/`, and fails clearly if `scripts/sign_manifest.py` is missing from the checked-out tooling ref. It then signs generated `stable.json` into `stable.signed.json` with `scripts/sign_manifest.py`, key ID `bus-core-prod-ed25519-2026-04-25`, and GitHub secret `BUSCORE_MANIFEST_SIGNING_PRIVATE_KEY`. If that secret is missing, the workflow fails clearly and does not silently publish an unsigned manifest.
16. The workflow verifies that the signed manifest preserves `latest.version` and `latest.download.url`, contains `signature.alg = Ed25519` and the expected key ID, and verifies the embedded signature using Core's pinned public key policy before upload.
17. The signed manifest is uploaded in place to R2 as `manifest/core/stable.json`. Lighthouse serves/proxies that manifest, but Lighthouse does not own signing authority; the GitHub Actions release workflow does.
18. `.github/workflows/publish-image.yml` remains a separate container-publish workflow and does not govern Windows release/update version authority.

Release-mirror publication is not atomic: the versioned R2 release asset is uploaded before manifest signing/verification and stable-manifest overwrite. A later failure can leave a partial external mutation requiring separately approved reconciliation. Manual release-mirror dispatch is a publishing mutation, not a diagnostic or harmless backfill: it uses current default-branch tooling, uploads release content to R2, and can repoint the stable manifest to an older requested tag. It requires explicit owner approval. Any push to `main` also triggers GHCR publication, including documentation-only pushes; qualifying wiki-path changes pushed to `main` trigger public wiki publication through `.github/workflows/publish-wiki.yml`.

## Docker Deployment Boundary

BUS Core is local-first software. The default Docker Compose runtime publishes the app to host loopback only with `127.0.0.1:8765:8765`; the container-internal Uvicorn bind remains `0.0.0.0` so Docker networking works. BUS Core is not safe for LAN or public exposure by default because `/session/token` is a local bootstrap surface and the default session model is for local loopback use, not multi-user network hosting.

Any non-loopback deployment requires explicit operator action, a clearly named override such as `docker-compose.lan.yml`, and stronger access controls around the host, network, reverse proxy, and session bootstrap path. Bare default host publishing such as `8765:8765` is not permitted in `docker-compose.yml`.

This flow is trustworthy to the extent that version authority is singular and machine-checked, release manifests are signed, and manual staging now fails closed on unsigned or untrusted manifest metadata. It is not yet a fully automated end-to-end updater, and the docs should not imply otherwise.

Manifest compatibility is a release boundary for this bridge release: deployed clients must still find top-level `latest.version` and `latest.download.url`, while newer clients may additionally read additive metadata, `channels.<channel>` entries, and a top-level embedded `signature`. `channels.stable` should mirror top-level `latest` unless a release owner intentionally documents a divergence. The embedded signature covers deterministic canonical JSON of the manifest after removing top-level `signature`.

## Observed Update Check Flow

1. The sidebar startup controller calls `GET /app/update/check?source=startup`; Settings `Check now` calls `GET /app/update/check?source=manual`. Home consumes the startup result and does not issue another request.
2. The backend enforces `updates.enabled` and `updates.check_on_startup` for startup requests and executes at most one startup check per app launch. Manual `Check now` remains available regardless of those two automatic-check gates.
3. Route loads the configured `updates.channel` and `updates.manifest_url` from `%LOCALAPPDATA%\BUSCore\config.json`.
4. `UpdateService.check()` validates the current runtime version as strict SemVer.
5. Service validates the manifest URL and configured channel, fetches JSON with timeout and size caps, normalizes supported manifest shapes, supports signed manifest unwrapping when present, validates optional metadata shape, and compares the selected release version against runtime `VERSION`. Non-staging discovery preserves unsigned-manifest compatibility but is not evidence-neutral.
   - The outbound check request appends three aggregate-safe query params to the manifest URL: `current_version` (runtime `VERSION`, omitted if not strict SemVer), `channel` (validated low-cardinality lane, falling back to `stable`), and installation-level `first_check` (`true` while this local profile's reported flag is false, `false` after successful persistence, and never reset for a version). Any pre-existing query params on `updates.manifest_url` are preserved; the app-provided values win on key collision. Core's generated fields add no install/device/user ID, hostname, username, machine fingerprint, or dedupe/persistent-client token, but operator-configured URL userinfo and preserved query extras are not prohibited/sanitized and are trust-sensitive outbound data. `update_check_first_reported` is a single local boolean in `%LOCALAPPDATA%\BUSCore\config.json`; every performed check while it remains false retries the best-effort write, including after request error, and only a successful write makes later checks send false without rewriting.
   - The current Lighthouse aggregate counts only requests with exactly one of each canonical parameter and no extras that also pass receiver validation/rate policy. Extra configured query parameters can still yield a manifest response but zero route count; a custom manifest host yields no Lighthouse route count. `first_check` is a profile flag, not a unique-install count or receipt proof.
6. Route returns normalized release keys `current_version`, `latest_version`, `update_available`, `download_url`, `error_code`, `error_message` plus `check_source`, `check_performed`, and nullable `skip_reason` so callers can distinguish a real check from a policy or same-launch skip.
7. UI shows a manual Update button when `update_available` is true.
8. Clicking Update calls `POST /app/update/stage` (session + `updates.stage` + write-gated), re-fetches the configured manifest without the update-analytics tuple, requires a trusted signed manifest, then performs hash-verified ZIP download, safe extraction, EXE trust verification, and conservative version+sha keyed `verified_ready_versions` promotion. Legacy `verified_ready` is refreshed as the compatibility/latest record and remains an active read/handoff fallback for valid older state.
9. Successful staging reports verified-ready state and instructs restart/reopen; no forced restart endpoint is invoked.
10. On next start, launcher evaluates the effective verified-ready record set after DB lock—keyed records plus any valid non-duplicate legacy `verified_ready` fallback—filters to versions newer than the running `VERSION`, selects the newest eligible SemVer candidate, and applies verified launch policy without overwriting the running EXE.

Update checks are part of the trust model because they are optional and non-blocking. Core remains usable without them, and an unavailable manifest host should not prevent normal local operation.

The update-check parameters are distinct from the broader product-telemetry contract. The client removes a product event and completes a deduplicated milestone only after Lighthouse acknowledges that exact event ID. Release order is mandatory: deploy and verify the compatible Lighthouse receiver before releasing this BUS Core client. The client retains fail-open local operation and prohibits business-content payloads.

## Implemented vs documented vs assumed release/update elements

| Element | Implemented in code | Documented only | Assumed by tooling | Status |
| --- | --- | --- | --- | --- |
| Runtime version source | Yes | Yes | Yes | Canonical |
| Release-triggered tag must equal `VERSION` | Yes | Yes | Yes | Canonical for release-triggered publication; manual historical backfill is the documented exception. |
| Published manifest `latest.version` from `VERSION` | Yes for release-triggered runs | Yes | Yes | Canonical for new release publication; manual backfill derives it from the requested tag. |
| Default manifest URL | Yes (`lighthouse.buscore.ca/update/check`) | Yes (`lighthouse.buscore.ca/update/check`) | No | Canonical |
| Manual update check UI | Yes | Yes | No | Canonical |
| Startup update notice | Yes | Yes | No | Canonical |
| Manifest channel support | Yes | Yes | No | Canonical |
| Embedded manifest signing publication | Yes | Yes | Yes | Canonical |
| Client requires signed manifest | Partial by deliberate route boundary | Yes | No | `/app/update/stage` requires signed manifests; public non-staging discovery keeps unsigned compatibility. |
| Local update cache/state | Yes | Yes | No | Canonical for guarded staging and next-start handoff |
| `hash_verified` state from real artifacts | Yes | Yes | No | Conservative state only; downloaded ZIP matched signed manifest metadata |
| `extracted` state from real artifacts | Yes | Yes | No | Conservative state only; safe ZIP extraction completed, but executable trust is not established until EXE verification succeeds |
| `exe_verified` state from real artifacts | Yes | Yes | No | Conservative state only; extracted EXE passed Authenticode, True Good Craft subject, and pinned-thumbprint checks |
| `verified_ready_versions` state from real artifacts | Yes | Yes | No | Conservative version+sha keyed current write authority; written only when prior cache stages agree and confined files still exist. Legacy `verified_ready` is the compatibility/latest record and remains an active read/handoff fallback for valid older state. |
| Release notes link from manifest | Declared metadata only | Yes | No | Not an execution authority |
| Manifest checksum/hash use | Yes in guarded stage | Yes | No | Trusted signed metadata drives ZIP hash/size verification |
| Artifact signature/publisher/size verification | Yes in guarded stage | Yes | No | ZIP hash/size plus EXE Authenticode/publisher/thumbprint verification are active manual-stage requirements; discovery does not execute artifacts |
| Binary signing execution | Yes, in `scripts/build_core.ps1` when `-Sign` or `-Release` is used | Yes | No | Canonical for local build/sign/bundle only; external publication stays separate. |
| Truthful release-check helper | Yes | Yes | Yes | Canonical |

## External infrastructure references

| Reference | Status | Where it appears | Notes |
| --- | --- | --- | --- |
| `https://lighthouse.buscore.ca/update/check` | Canonical | `core/config/manager.py` default updates config, `SOT.md` | Current default update endpoint. |
| `https://lighthouse.buscore.ca/telemetry/v1/events` | Canonical immutable client endpoint | `core/telemetry/client.py`, `SOT.md`, `OPERATIONS.md` | Independent consent-gated product-event stream; not redirected by manifest config. |
| `https://buscore.ca` | Secondary | `README.md` | Public site reference only. |
| GHCR `ghcr.io/true-good-craft/tgc-bus-core` | Canonical | README + publish workflow | Container distribution path. |

## Fragile coupling points

| Coupling point | Status | Why it matters |
| --- | --- | --- |
| `core/version.py` vs docs/governance text | Secondary | Runtime/build/workflow truth is canonical in code; human docs must stay in sync. |
| `scripts/release-check.ps1` vs actual smoke/build chain | Canonical | Helper now validates the real current scripts and artifact names. |
| Governance guard workflow bypass | Narrowed drift | General automation remains sparse, but version and change-trace governance now fail through an active dedicated workflow. |
| Update check and stage split | Canonical | Public `/app/update/check` is non-staging but evidence-mutating; `/app/update/stage` is protected and write-gated trusted staging. |
| Release history in manifest | Narrowed drift | Current release publication is canonical, but history still reflects GitHub release metadata filtered by canonical `BUS-Core-*.zip` assets. |
| Manifest signing key custody | Canonical but operational | Private key lives outside repo in GitHub secret `BUSCORE_MANIFEST_SIGNING_PRIVATE_KEY`; public key is pinned in Core. |

Release and update trust here depends more on clear authority and honest limits than on a large automation footprint. The current boundary is: canonical version authority exists, authority mirrors and change-trace requirements are machine-checked, release-triggered tag alignment is checked, the explicitly approved manual historical-backfill path is documented as an exception, manifests are signed during publication, update-check metadata is normalized, channel-specific manifests are selected explicitly, manual staging requires trusted signed manifest metadata before executing artifact verification into version+sha keyed `verified_ready_versions`, and launcher handoff is policy-controlled on next start.

Known remaining release/update work is explicit: deciding whether non-staging discovery should also require signed manifests, adding optional restart orchestration beyond restart/reopen guidance, and Docker release hardening if the container lane needs governed releases. The schema-1.0 receiver/migration baseline was deployed and production-verified at Lighthouse 1.27.0 with migration 0015; Lighthouse's own SOT governs its current deployed version. There is still no auto-install, startup auto-update, or silent background update behavior.

## Freeze Notes

- Refresh on: version bumps, build script/spec changes, update-service changes, manifest URL changes, workflow changes, or signing/validation changes.
- Fastest invalidators: changing the canonical version source, changing release asset naming, weakening staging signed-manifest enforcement, disabling security-audit workflow evidence, adding new artifact trust stages, or rewriting release publication flow.
- Check alongside: `02_API_AND_UI_CONTRACT_MAP.md` for `/app/update/check` contract shape and `04_SECURITY_TRUST_AND_OPERATIONS.md` for update-path security implications.

## Internal Version Boundary

- `VERSION` remains the public authority for new release tags, release-triggered manifest `latest.version`, and update comparison logic; an owner-approved manual historical backfill derives the mirrored version from its requested existing tag without changing current `VERSION`.
- `INTERNAL_VERSION` is for repo working-revision tracking only.
- On release-triggered runs, `.github/workflows/release-mirror.yml` machine-checks `tag == v{VERSION}` and tag/default-branch target alignment before publishing release metadata. Manual dispatch is the documented historical-backfill exception and performs neither check.
- Remaining unresolved drift is narrow and explicit: manifests are signed during release publication, staging requires a trusted signed manifest, non-staging discovery keeps unsigned compatibility and changes analytics evidence when performed; metadata may be retained as declared values; manual `/app/update/stage` executes trusted ZIP hash/extract/EXE verification into `verified_ready_versions`; and release history still depends on GitHub release metadata plus matching BUS-Core assets.

## Manifest Key Rotation

- Add the new production public key to `core/runtime/manifest_keys.py` as active.
- Publish manifests signed with the new key ID after clients have the new public key.
- Mark the old key deprecated while older clients migrate.
- Revoke or remove the old key only after supported clients trust the replacement.
