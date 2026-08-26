# Security Policy

## Reporting a Vulnerability

Please report suspected vulnerabilities privately through one of these channels:

- [GitHub private vulnerability reporting](https://github.com/True-Good-Craft/TGC-BUS-Core/security/advisories/new), when the repository's **Report a vulnerability** action is available.
- Email `truegoodcraft@gmail.com` with the subject `BUS Core security report` if private GitHub reporting is unavailable.

Include:

- Affected file(s) and function(s)
- Reproduction steps and required inputs
- Expected impact and trust boundary crossed
- Suggested fix or mitigation (optional)

Do not open public issues for unpatched security defects.

BUS Core `1.4.x` is the currently supported release line. Security fixes are prepared on a branch, verified against the supported runtime and release targets, and released only after owner approval. Do not send live credentials, private business data, or an unredacted production database with a report.

## Bandit Policy (BUS Core)

This repository uses Bandit to improve real security posture, not to force scanner-clean refactors.

Rules:

- Preserve canonical authority surfaces and API/runtime contracts.
- Prefer minimal diffs and behavior-preserving fixes.
- Avoid broad global skips.
- Use narrow suppressions only when findings are false positives or intentional fail-soft behavior.
- Suppressions must not replace real fixes when findings touch integrity-relevant boundary logic (for example, path-token or trust-boundary resolution paths).
- Compatibility-preserving security hardening may use old-read/new-write transitions when needed to avoid breaking valid standing state while strengthening new emissions.

Current CI security workflow: `.github/workflows/security-audit.yml`.

- Bandit runs on `core`, `tgc`, `scripts`, and `launcher.py`.
- Low-severity Bandit findings are reported in advisory mode.
- Medium and High Bandit findings fail CI.
- `pip-audit` blocks on the hash-locked Python 3.12 Linux and Python 3.11 Windows dependency graphs.
- General CI installs those same reviewed locks and runs the regression suite on both targets.

This security workflow and the April/August 2026 hardening passes are internal repository hardening evidence. They are not an independent audit, penetration test, OWASP certification, enterprise-readiness claim, or proof that BUS Core is safe for LAN/public multi-user hosting by default.

Known remaining work includes structured security audit events, backup/restore operator safeguards, further fallback-secret hardening, and explicit plugin/provider trust-boundary enforcement.

Current workflow exclusions are limited to tests, build/runtime outputs, virtual environments, caches, and local temporary tooling directories:

- `.venv`
- `build`
- `dist`
- `tests`
- `.pytest_cache`
- `.tmp_test_deps_*`
- `.tmp_localappdata_*`
- `.gate-pytest-*`
- `.artifacts`

## Suppression Standard

Every suppression must be:

- Narrow: tied to a specific line or call site
- Justified: include an inline rationale
- Audited: recorded in `docs/security/remediation_audit_log.md`

Patterns that can be acceptable with narrow suppression:

- Controlled SQL fragments from internal allowlists/fixed keys
- Non-security hash usage for local identifiers
- Validated URL opens on fixed allowlisted endpoints
- Intentional cleanup/fail-soft exception handling
