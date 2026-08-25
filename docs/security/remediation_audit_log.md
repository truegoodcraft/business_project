# Bandit Remediation Audit Log

Date: 2026-04-23
Last remediation update: 2026-08-25

## Entries

| File | Finding ID | Classification | Action Taken | Rationale |
| --- | --- | --- | --- | --- |
| `pyproject.toml` | policy baseline | DOCUMENTATION CORRECTION | No `[tool.bandit]` baseline is present in the current file; prior wording that claimed one was added was documentation drift | Do not claim Bandit exclusions or a pyproject Bandit baseline until the file actually contains one. |
| `core/api/http.py` | B608 | NARROW SUPPRESSION (EXACT-LINE RETAINED) | Removed inline `# nosec B608` for stale-check, re-ran Bandit on file, observed B608 at the same query line, then restored suppression on that exact line only | Query values remain parameterized with DB-API placeholders; scanner still flags dynamic placeholder assembly. |
| `core/ledger/health.py` | B608 | TRUE FIX | Replaced dynamic column interpolation with two static query variants (`qty` / `qty_stored`) | Removes string-formatted SQL while preserving existing runtime behavior and schema compatibility. |
| `core/utils/export.py` | B608 | NARROW SUPPRESSION | Added inline `# nosec B608` on table-count query | Table identifier comes from fixed internal dictionary keys only. |
| `core/runtime/sandbox.py`, `core/runtime/sandbox_runner.py`, `core/ui/js/router.js`, `core/ui/js/cards/admin.js`, `core/api/http.py`, `core/utils/export.py`, `core/utils/pathsafe.py` | CodeQL hardening pass | TRUE FIX | Fixed sandbox argv to BUS Core-owned runner args with stdin JSON payloads, removed legacy router dynamic dispatch, replaced admin preview `innerHTML` metadata rendering with text-safe DOM construction, and constrained import/local/plugin paths to explicit allowed roots | Hardening addresses the recorded command-construction, DOM-XSS, and path-injection boundary issues; GitHub CodeQL re-scan after push/PR remains the confirmation source. |
| `core/reader/ids.py`, `core/reader/api.py`, `core/plans/commit.py`, `tests/test_reader_rid_security.py` | B324 | TRUE FIX + COMPATIBILITY HARDENING | Replaced active RID signature generation with hardened v2 generation (`local:v2:<sig32>:<payload>`), retained strict legacy read compatibility (`local:<sig10>:<payload>`), enforced strict fail-closed RID parsing/decoding/path checks, and tightened commit RID authority for present RID fields | Resolves integrity-relevant RID boundary weakness via real hardening without suppression/workarounds while preserving standing product compatibility for valid legacy values. |
| `plugins/notion/plugin.py` | B310 | TRUE FIX + NARROW SUPPRESSION | Added strict URL allowlist check (`https://api.notion.com`) and inline `# nosec B310` at `urlopen` | Runtime path now enforces scheme/host policy before network open; scanner warning is retained as documented suppression due generic `urlopen` rule. |
| Python source | Empty except / B110 | TRUE FIX + POLICY GUARD | Classified 72 empty handlers, replaced journal side-effect silence with safe type-only warnings, narrowed selected compatibility catches, made fallback secret-delete failures controlled errors, documented intentional non-fatal handlers, and added a source guard for undocumented empty handlers | Swallowed exceptions are allowed only for documented cleanup/fallback/journal/cache cases; raw exception details and sensitive values must not be returned or logged. |
| `core/ui/app.js`, `core/ui/js/cards/manufacturing.js`, `core/ui/js/cards/jobs.js` | DOM injection sinks | TRUE FIX | Replaced dynamic `innerHTML` interpolation for route hashes, manufacturing history values, and API error messages with DOM nodes and `textContent`; added executable hostile-payload tests | URL fragments and backend-originated text must never be parsed as application HTML. |
| `core/appdata/paths.py`, `core/services/capabilities/registry.py`, `core/secrets/manager.py`, `core/config/tracker.py`, `tgc/settings.py` | Runtime path authority | TRUE FIX | Made explicit BUS Core roots take precedence over legacy home fallbacks and changed encrypted secret paths from import-time constants to use-time resolution | Keeps test, managed, and explicitly configured runtime state inside the selected authority root and prevents stale-path writes. |
| Dependency manifests, locks, Dockerfile | Vulnerable floors / unpinned dependencies | TRUE FIX | Raised affected direct-dependency floors; generated hashed Linux/Windows lock graphs; pinned the Python image digest | Latest-resolution audit success is now backed by deterministic install inputs rather than floating ranges. |
| `.github/workflows/*` | Scorecard pinning / token permissions | TRUE FIX | SHA-pinned action dependencies, restored active test CI, made locked audits blocking, and moved publishing writes to job scope | Reduces mutable workflow dependencies and limits token authority while preserving release, image, and wiki operations. |

## Classification Notes (Current Snapshot)

- `core/api/http.py` still emits a Bandit `nosec encountered (B608), but no failed test` warning with the exact-line suppression in place; suppression is retained because removing it reproduces B608 at the same line.
- `pyproject.toml` currently contains project metadata only; Bandit configuration remains unset unless a future change adds `[tool.bandit]`.
- `B105` findings in provider/plugin response payload defaults are treated as FALSE POSITIVES unless a real secret literal is present.
- `B101` in tests is accepted test-scope noise.
- `B110/B112` are mostly intentional fail-soft/cleanup paths and require selective future cleanup, not blanket rewrites.
- Empty exception handlers now require a narrow exception type where practical plus safe logging or an approved explanatory comment; `tests/test_empty_except_guard.py` blocks undocumented `except ...: pass` reintroductions in source files.
- `B603/B607/B404` around subprocess usage are context-dependent; current runtime patterns should be hardened only when trust-boundary input reaches command arguments.
- RID hardening verification completed with targeted commands: `python -m bandit -r core/reader/ids.py core/reader/api.py core/plans/commit.py core/organizer/api.py --exclude ./.venv,./build,./dist` and `pytest -q tests/test_reader_rid_security.py`.
