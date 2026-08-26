# BUS Core Operations and Analytics Diagnostics

This is the canonical repeatable procedure for BUS Core operational diagnosis, especially Lighthouse alerts, update-check analytics, and product telemetry. It is subordinate to `SOT.md` and governed by `AGENTS.md`.

The default diagnostic posture is repository-only and zero-network. Expand access one level at a time only when the task explicitly authorizes that evidence source.

## 1. Evidence ownership

| System | Owns | Does not prove |
| --- | --- | --- |
| BUS Core | Consent/config, event construction, local queue/state/dead letter, update-check request construction, configured manifest host, staging and launcher handoff | Lighthouse receipt beyond a processed exact acknowledgement; receiver aggregate health; Agent Smith notification delivery |
| Lighthouse | Manifest/update receiver behavior, exact product-event acknowledgement, aggregate storage, receiver/rate/error evidence | Local consent, local queue contents, feature use that never reached it, unique installs, people, engagement, or retention |
| Agent Smith | Lighthouse report formatting, WATCH/ALERT evaluation, Discord/report orchestration | BUS Core local state or the cause of a missing downstream signal |
| `buscore-site` | Linked public privacy/support content | Native client delivery state or receiver health |

There is no direct Agent Smith-to-BUS Core call. Agent Smith is downstream of Lighthouse. A missing or unusual downstream count cannot by itself distinguish opt-out, no feature use, local write failure, backoff, dead letter, process exit, malformed local state, network failure, receiver rejection, or reporting delay.

## 2. Access levels

Record the highest level actually used.

| Level | Access | Default effect |
| --- | --- | --- |
| `R0_REPO` | Checked-in files and Git metadata only | Zero runtime, local-state, or network mutation |
| `R1_LOCAL_STATE` | Direct read of explicitly approved `%LOCALAPPDATA%\BUSCore` files | No mutation when files are read directly; exposes operator-local evidence |
| `R2_RUNNING_LOCAL` | Approved calls to an already-running loopback instance | Writes request logs; claimed auth may touch session `last_seen_at` |
| `R3_EXTERNAL` | Approved Lighthouse, Agent Smith, Cloudflare, Discord, or other external evidence | Surface-specific; `GET`/`HEAD` are not assumed passive. Follow the target service's canonical access procedure and record every production interaction. |

If required evidence is above the approved level, report `ACCESS_BLOCKED`. Do not elevate evidence by launching BUS Core, forcing a check, flushing telemetry, saving a preference, or staging an update.

## 3. Two independent Lighthouse signal streams

### 3.1 Update-route discovery signal

BUS Core's default manifest URL is:

`https://lighthouse.buscore.ca/update/check`

An actual update check sends an HTTP `GET` to the configured manifest URL with:

- `current_version` — strict public `VERSION` when valid;
- `channel` — one allowed low-cardinality release channel;
- `first_check` — installation-profile boolean backed by top-level config key `update_check_first_reported`.

After any request attempt made while the flag is false, including an error, the client makes a best-effort write marking `first_check` as reported. When that write succeeds, later checks send `false` and do not rewrite the flag. If persistence fails, a later performed check again sends `first_check=true` and retries the write. It is not version-specific, is not proof of receipt, and is not a persistent identifier.

BUS Core preserves unrelated query parameters already present in `updates.manifest_url` while replacing its three canonical keys. Core's three generated parameters carry no identity, but operator-supplied URL userinfo and query parameters are not prohibited/sanitized and therefore remain operator-controlled, trust-sensitive outbound data. Under the current Lighthouse receiver contract, a request contributes to the update-route aggregate only when exactly one of each canonical parameter is present and no additional query parameters are present, the values pass receiver validation, the channel is serviced, a usable Cloudflare source IP and receiver rate-secret configuration exist, the source is not ignored, and the request remains within the current allowance of two counted checks per source IP per UTC day. The current plausible-version window is `>=1.4.0` and not newer than Lighthouse's served latest version. Therefore:

- a successful manifest response is not proof that the request was counted;
- a configured Lighthouse URL with extra query parameters can serve a manifest while producing zero update-route count;
- a custom manifest host produces no Lighthouse update-route count.

The route aggregate is rate-bounded receiver evidence, not a count of people, authenticated clients, installations, adoption, or active users.

### 3.2 Product-event signal

The native client endpoint is immutable in current code:

`https://lighthouse.buscore.ca/telemetry/v1/events`

It is independent of the configured update manifest host. A custom manifest host does not redirect product telemetry. `BUS_DEV=1` and the public-site `dev_mode` cookie do not suppress or reroute the native client.

Transmission requires both:

- `telemetry.enabled == true`; and
- `telemetry.disclosure_acknowledged == true`.

Current defaults are enabled `true` and disclosure acknowledged `false`, so nothing is transmitted until disclosure is persisted. The strict schema-1.0 payload contains only:

- `schema_version`;
- UUIDv4 `event_id`;
- allowlisted `event_name`;
- `client_ts`;
- `context.app_version`;
- `context.release_channel`;
- `context.os_category`.

No arbitrary business fields or persistent installation identifier can enter through the public emitter.

Current implementation allowlist, with authority status made explicit:

| Category | Event names |
| --- | --- |
| Installation/release | `installation_first_launch`, `version_first_seen`, `update_check_startup`, `update_check_manual`, `update_staged`, `update_failure` |
| SOT-authorized workflow milestones | `first_stock_recorded`, `first_contact_created`, `first_recipe_created`, `first_manufacturing_run_completed`, `first_job_completed`, `first_invoice_issued`, `first_finance_entry_recorded`, `first_backup_exported` |
| Reliability | `startup_failure`, `backup_failure`, `restore_failure`, `unhandled_application_error`, `migration_failure` |
| Implemented outside the current SOT-authorized signal set | `restore_attempted`, `restore_completed`, `import_completed`, `import_failed` |

`installation_first_launch`, version-keyed `version_first_seen`, and event names beginning with `first_` are locally deduplicated milestones. Their milestone keys are committed only after exact acknowledgement. Other allowlisted events are not milestone-deduplicated.

The four repeatable restore/import outcomes are a blocking code/SOT/privacy-document conflict, not an approved expansion. They can appear in live local or Lighthouse evidence because current code emits them, but this runbook does not authorize them. An owner must separately choose either code conformance removal or a behavior/SOT/changelog/privacy/test bundle.

The streams can legitimately diverge. Never add them together or substitute one for the other.

## 4. Checked-in endpoint contract

| Method and path | Auth/current guard | Operational meaning |
| --- | --- | --- |
| `GET /health` | Public | Process reachability and public version only |
| `GET /app/telemetry/status` | Mode-appropriate session + `settings.read` | Local delivery snapshot; does not flush or contact Lighthouse |
| `POST /app/telemetry/preference` | Mode-appropriate session + `settings.read`; intentionally outside business write gate | Persists disclosure/preference; enable attempts to emit eligible startup milestones; disable blocks new emits/new flush starts and best-effort overwrites queue/dead-letter files with empty arrays, but does not cancel an already in-flight sender request |
| `POST /app/config` | Mode-appropriate session + `settings.manage` + write gate | Persists config. A telemetry section can attempt eligible startup milestone emission or perform the same best-effort opt-out clearing as the preference route. |
| `GET /app/config` | Mode-appropriate session + `settings.read` | Runtime config snapshot |
| `GET /app/update/check?source=startup|manual` | Exact public GET exception; no route-local permission | Performs or skips an update check according to source policy; a performed check changes local/remote evidence |
| `POST /app/update/stage` | Session + `updates.stage` + write gate | Re-fetches trusted manifest and mutates update cache/state while staging an artifact |

Manual update checks always run. Startup checks alone honor `updates.enabled`, `updates.check_on_startup`, and the once-per-launch cache.

## 5. Side-effect matrix

| Action | Network | Local mutation/evidence | Diagnostic classification |
| --- | --- | --- | --- |
| Read checked-in repository files | No | None | Passive |
| Directly read selected config/telemetry JSON after approval | No | None | Passive local-state read |
| Run `git status`, `git diff`, or static validators | No | Git may read metadata; validators must not import/start runtime | Passive repository validation |
| Call `/health` on an already-running instance | Loopback | Request-log append | Read-mostly; proves only process/version |
| Call `/app/telemetry/status` on an already-running authorized instance | Loopback | Request-log append; claimed session may update `last_seen_at` | Read-mostly local snapshot, not a receiver probe |
| Call `/app/config` on an already-running authorized instance | Loopback | Request-log append; claimed session may update `last_seen_at` | Read-mostly config snapshot |
| Call `/transparency.report` | Loopback | Request-log append; possible claimed-session touch | Not telemetry authority; current report hardcodes telemetry off |
| Call `GET /app/update/check` | Outbound manifest request | Request log; possible telemetry enqueue/delivery and Lighthouse count/rate/error evidence; while the reported flag remains false, each performed call also retries the best-effort config write | Active probe; forbidden for passive diagnosis |
| Load/start/import BUS Core | May contact Lighthouse/other configured services | Locking, initialization/migrations, indexing, logs, startup events, queue flush, other startup state | Mutating; never use to obtain a passive snapshot |
| Save telemetry preference or write telemetry fields through `/app/config` | Possible product-event delivery when enabling; an already in-flight request is not cancelled when disabling | Config write; enable attempts eligible startup milestone emission; disable blocks new emits/new flush starts and best-effort overwrites queue/dead-letter files with `[]` | Mutating control action |
| Invoke telemetry flush | Lighthouse POST | Queue/state/dead-letter updates | Active delivery action |
| Stage an update | Manifest/artifact requests | Downloads, extracted files, update state, logs, telemetry | Full mutation |

HTTP `GET` does not mean zero side effects. The update-check route is the critical counterexample.

## 6. Local state authority

Canonical Windows files:

| Path | Meaning |
| --- | --- |
| `%LOCALAPPDATA%\BUSCore\config.json` | `telemetry.*`, `updates.*`, and top-level `update_check_first_reported` |
| `%LOCALAPPDATA%\BUSCore\state\telemetry_state.json` | Cumulative counters, acknowledged milestone keys, last delivery status/error/time |
| `%LOCALAPPDATA%\BUSCore\state\telemetry_queue.json` | Current pending records, including records not yet retry-eligible |
| `%LOCALAPPDATA%\BUSCore\state\telemetry_dead_letter.json` | Newest retained rejected, overflowed, or retry-exhausted records, capped at 100 |
| `%LOCALAPPDATA%\BUSCore\updates\state.json` | Local update-cache and verified-ready state |

Interpretation rules:

- `acknowledged_count`, `rejected_count`, and `dead_letter_count` are cumulative.
- `pending_count` is the length of the currently readable queue and includes future-backoff records.
- The dead-letter file retains at most 100 records; its length can be lower than cumulative `dead_letter_count`.
- Telemetry state, pending records, and retained dead letters have no time-based expiry. Low-volume records can persist indefinitely until a lifecycle action or separately approved maintenance changes them.
- Disabling telemetry blocks new emits and new flush starts, but it does not cancel a sender request already in flight. It attempts best-effort replacement of pending and dead-letter file contents with empty JSON arrays while retaining telemetry-state counters, last fields, and acknowledged milestone keys. A successful preference/config response is not proof that those file writes succeeded.
- JSON writes are atomic per file but are not a transaction across state, queue, and dead-letter files.
- Malformed or unreadable telemetry JSON is treated by runtime code as empty/default. There is no quarantine. Starting the runtime or emitting afterward can overwrite evidence, so validate raw JSON before interpreting or launching anything.

## 7. Delivery, retry, and acknowledgement truth

Limits:

- pending queue: 100 events;
- retained dead letters: newest 100 records;
- one flush: at most 10 currently eligible events;
- request timeout: 2 seconds;
- maximum delivery attempts: 3.

Success requires both an HTTP 2xx response and the exact queued `event_id` in `acknowledged_event_ids`. A generic 2xx is not success; absence of the exact ID becomes `missing_acknowledgement`.

Outcomes:

- exact acknowledgement: remove from queue, increment acknowledgement count, set success time, clear last error, and commit any milestone key;
- non-429 4xx: immediate rejection and dead letter;
- 429, 5xx, transport error, invalid sender result, or missing acknowledgement: eligibility is delayed 1 second after the first failed attempt and 5 seconds after the second, then the record dead-letters on attempt three.

Retry is trigger-driven, not continuously scheduled. The worker performs one flush and exits when no record is currently eligible. A delayed record waits for a later emit, later startup, or explicit internal flush. The declared 30-second delay is not reached because attempt three dead-letters. Shutdown does not flush, join, or wait for the daemon telemetry worker. "At most three attempts" is not an eventual-delivery guarantee.

## 8. Status-field interpretation

`GET /app/telemetry/status` returns:

| Field | Meaning |
| --- | --- |
| `enabled` | Both consent fields are true; cannot distinguish awaiting disclosure from explicit opt-out |
| `pending_count` | Current readable queue length, including future-backoff records |
| `acknowledged_count` | Cumulative locally processed exact acknowledgements |
| `rejected_count` | Cumulative immediate non-429 4xx rejections |
| `dead_letter_count` | Cumulative overflow, rejection, and exhaustion count; not retained file length |
| `last_successful_delivery_at` | Local client time of latest processed exact acknowledgement |
| `last_status` | HTTP status from the latest attempted delivery, successful or not |
| `last_error_category` | Latest error category; cleared only by exact acknowledgement |

If status construction fails, counts/status fields are null, `enabled` is false, and `last_error_category` is `status_unavailable`. The status route is a local snapshot and never proves current Lighthouse health.

## 9. Delivery-proof hierarchy

Use the strongest available level and state it explicitly:

1. `PROOF_NONE` — configuration, an empty queue, UI text, health, or absence downstream; no delivery proof.
2. `PROOF_LOCAL_PENDING` — valid queue/dead-letter evidence describes local state only.
3. `PROOF_LOCAL_AGGREGATE_ACK` — increased acknowledgement counter/last-success proves some exact acknowledgement was processed locally, not which non-milestone event after removal.
4. `PROOF_LOCAL_MILESTONE_ACK` — a stored milestone key proves that milestone received an exact acknowledgement.
5. `PROOF_IN_FLIGHT_EXACT_ACK` — captured 2xx response containing the exact event ID is strongest event-specific proof.

Lighthouse aggregate totals and Agent Smith reports are receiver/report evidence, not per-install delivery proof. BUS Core does not persist acknowledged event IDs after queue removal except via milestone keys.

## 10. Known non-authoritative surfaces

Do not use these as telemetry truth:

- Home currently hardcodes `Telemetry: Off`.
- `/transparency.report` currently hardcodes `"telemetry": "off"`.
- The first-run disclosure catches preference-save failures, dismisses itself without an error, and can therefore reappear on the next load because consent was not persisted. A click/dismissal is not proof that the preference saved.
- The startup trust banner reflects consent/config state, not queue or receiver health.
- `/health` proves only a responding process and public version.
- An empty queue can mean acknowledged, rejected, exhausted, cleared, overflowed, unreadable, or never queued.
- A successful update check does not prove a counted update-route request or a product-event acknowledgement.
- `first_check=true` is not proof of a unique installation or a first check for the current version.
- Missing Lighthouse/Agent Smith evidence is not proof of opt-out or inactivity.
- Repeatable restore/import events can appear because of the known code/SOT conflict; their presence is implementation evidence, not proof that the signal set was approved.

The Home/transparency displays and silent first-run preference-save failure are known implementation drift. Correcting them is a separate code/SOT/changelog/version/test bundle.

The packaged `license/PRIVACY.md` and its truth test still describe opt-out queue clearing categorically, while implementation is best-effort, also targets retained dead letters, retains cumulative state, and cannot cancel an in-flight request. That public/package contract is outside this approved local-doc set and requires a separate owner-approved privacy/test bundle. Existing wiki/release-note projections also pin Lighthouse 1.27.0 as if it were the current Worker rather than the verified schema-1.0 baseline; synchronize them separately because main-branch wiki edits can publish externally. The generated `TGC-COMPLIANCE.md` snapshot predates `AGENTS.md`/`OPERATIONS.md`; its estate-owned source must be updated and re-projected from `tgc-ops` under separate approval.

## 11. Morning alert procedure

### Step 1 — Preserve the alert

Record without transforming:

- alert source and exact label;
- UTC and local timestamps;
- report window/day key;
- affected metric, expected threshold, observed value, and severity;
- Agent Smith/Lighthouse version or report identifier when available.

Do not infer BUS Core cause from alert wording.

### Step 2 — Establish repository truth (`R0_REPO`)

Read only:

```powershell
git status --short --branch
git rev-parse HEAD
Get-Content -LiteralPath .\core\version.py
```

Then read `AGENTS.md`, `SOT.md`, this runbook, and only the relevant code/contracts. Confirm whether the alert concerns update-route GET evidence, product-event POST evidence, receiver errors/rates, or Agent Smith presentation.

### Step 3 — Determine the owning failure domain

- Request construction, consent, queue, retry, local counters: BUS Core.
- Count eligibility, HTTP acknowledgement, receiver aggregation/rate/error: Lighthouse.
- WATCH/ALERT evaluation or notification formatting/delivery: Agent Smith.

Do not cross-attribute without evidence.

### Step 4 — Inspect approved local state (`R1_LOCAL_STATE` only)

Validate existence, JSON syntax, and top-level shape before interpretation. Missing files are legitimate evidence; report them as `absent`. Output selected fields and aggregates only, never whole config, URL query values, payloads, or event identifiers. The example is compatible with Windows PowerShell 5.1 and does not import or launch BUS Core.

```powershell
$busCoreRoot = Join-Path $env:LOCALAPPDATA 'BUSCore'
$stateRoot = Join-Path $busCoreRoot 'state'
$paths = @(
  [PSCustomObject]@{ label = 'config'; path = (Join-Path $busCoreRoot 'config.json'); top = 'object' },
  [PSCustomObject]@{ label = 'telemetry_state'; path = (Join-Path $stateRoot 'telemetry_state.json'); top = 'object' },
  [PSCustomObject]@{ label = 'queue'; path = (Join-Path $stateRoot 'telemetry_queue.json'); top = 'array' },
  [PSCustomObject]@{ label = 'dead_letter'; path = (Join-Path $stateRoot 'telemetry_dead_letter.json'); top = 'array' }
)

function Read-JsonEvidence {
  param([string]$Label, [string]$LiteralPath, [ValidateSet('object','array')][string]$Top)
  if (-not (Test-Path -LiteralPath $LiteralPath -PathType Leaf)) {
    return [PSCustomObject]@{ label = $Label; status = 'absent'; data = $null }
  }
  try {
    $raw = Get-Content -LiteralPath $LiteralPath -Raw -ErrorAction Stop
    $trimmed = $raw.TrimStart()
    $shapeOk = (($Top -eq 'object') -and $trimmed.StartsWith('{')) -or
               (($Top -eq 'array') -and $trimmed.StartsWith('['))
    if (-not $shapeOk) {
      return [PSCustomObject]@{ label = $Label; status = 'invalid_top_level_shape'; data = $null }
    }
    $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
    return [PSCustomObject]@{ label = $Label; status = 'valid'; data = $parsed }
  } catch {
    return [PSCustomObject]@{ label = $Label; status = 'invalid_or_unreadable'; data = $null }
  }
}

$evidence = @{}
foreach ($entry in $paths) {
  $result = Read-JsonEvidence -Label $entry.label -LiteralPath $entry.path -Top $entry.top
  $evidence[$entry.label] = $result
  [PSCustomObject]@{ evidence = $result.label; status = $result.status }
}

if ($evidence.config.status -eq 'valid') {
  $config = $evidence.config.data
  $config.telemetry | Select-Object enabled, disclosure_acknowledged
  $config.updates | Select-Object enabled, check_on_startup, channel
  $config | Select-Object update_check_first_reported

  [Uri]$manifestUri = $null
  if ([Uri]::TryCreate([string]$config.updates.manifest_url, [UriKind]::Absolute, [ref]$manifestUri)) {
    $queryKeys = @($manifestUri.Query.TrimStart('?').Split('&') | Where-Object { $_ } | ForEach-Object {
      [Uri]::UnescapeDataString(($_ -split '=', 2)[0])
    })
    [PSCustomObject]@{
      manifest_scheme = $manifestUri.Scheme
      manifest_host = $manifestUri.Host
      manifest_path_is_update_check = ($manifestUri.AbsolutePath -eq '/update/check')
      manifest_has_userinfo = -not [string]::IsNullOrEmpty($manifestUri.UserInfo)
      manifest_is_canonical_lighthouse_route = (
        $manifestUri.Scheme -eq 'https' -and
        $manifestUri.Host -eq 'lighthouse.buscore.ca' -and
        $manifestUri.AbsolutePath -eq '/update/check' -and
        [string]::IsNullOrEmpty($manifestUri.UserInfo)
      )
      manifest_noncanonical_query_key_count = @($queryKeys | Where-Object { $_ -notin @('current_version','channel','first_check') }).Count
    }
  } else {
    [PSCustomObject]@{ manifest_url_status = 'invalid_absolute_uri' }
  }
}

if ($evidence.telemetry_state.status -eq 'valid') {
  $evidence.telemetry_state.data |
    Select-Object acknowledged_count,rejected_count,dead_letter_count,last_successful_delivery_at,last_status,last_error_category,milestones
}

$windowStartUtc = [DateTimeOffset]::UtcNow.AddHours(-24)
$windowEndUtc = [DateTimeOffset]::UtcNow
$nowEpoch = $windowEndUtc.ToUnixTimeSeconds()

if ($evidence.queue.status -eq 'valid') {
  $queue = @($evidence.queue.data)
  $queueInWindow = @($queue | Where-Object {
    [DateTimeOffset]$parsedTs = [DateTimeOffset]::MinValue
    [DateTimeOffset]::TryParse([string]$_.payload.client_ts, [ref]$parsedTs) -and
      $parsedTs -ge $windowStartUtc -and $parsedTs -le $windowEndUtc
  })
  [PSCustomObject]@{ queue_count = $queue.Count; queue_in_last_24h = $queueInWindow.Count }
  $queue | Group-Object { if ([double]$_.next_attempt_at -le $nowEpoch) { 'due' } else { 'deferred' } } | Select-Object Name,Count
  $queue | Group-Object -Property attempts | Select-Object Name,Count
  $queue | ForEach-Object { $_.payload.event_name } | Group-Object | Select-Object Name,Count
}

if ($evidence.dead_letter.status -eq 'valid') {
  $deadLetters = @($evidence.dead_letter.data)
  $deadInWindow = @($deadLetters | Where-Object {
    [DateTimeOffset]$parsedTs = [DateTimeOffset]::MinValue
    [DateTimeOffset]::TryParse([string]$_.failed_at, [ref]$parsedTs) -and
      $parsedTs -ge $windowStartUtc -and $parsedTs -le $windowEndUtc
  })
  [PSCustomObject]@{ retained_dead_letter_count = $deadLetters.Count; dead_letters_in_last_24h = $deadInWindow.Count }
  $deadLetters | Group-Object -Property attempts | Select-Object Name,Count
  $deadLetters | Group-Object -Property status | Select-Object Name,Count
  $deadLetters | Group-Object -Property error_category | Select-Object Name,Count
  $deadLetters | ForEach-Object { $_.payload.event_name } | Group-Object | Select-Object Name,Count
}
```

Stop if JSON is invalid. Preserve that fact; do not start BUS Core to see whether it recovers.

### Step 5 — Use local HTTP only if already running and authorized (`R2_RUNNING_LOCAL`)

Prefer direct file evidence. If an already-running instance and valid session are in scope, `/app/telemetry/status` may corroborate local state. Record the request-log/session-touch side effect. Do not launch the app to make this endpoint available.

Never use `/app/update/check` as a diagnostic probe.

### Step 6 — Inspect external evidence only when authorized (`R3_EXTERNAL`)

Before any external read, follow the target service repository's current `AGENTS.md` and canonical operations/access procedure. Use only a specifically approved diagnostic surface and credential context; do not discover access by fanning out across endpoints. Treat `GET` and `HEAD` by implementation effects, not as inherently passive. Use Lighthouse for receiver acceptance/rates/aggregates and Agent Smith for report evaluation, keeping GET update-route and POST product-event evidence separate. Record every production read and its time window. Do not send test events or force update checks unless the owner separately approves an active probe. If the canonical procedure, approved surface, or credential context is unavailable, report `ACCESS_BLOCKED` instead of improvising.

### Step 7 — Correlate and report

Normalize times to UTC, account for local retry eligibility and receiver/report windows, state the strongest proof level, and identify unknowns. Absence is reported as absence, not causation.

## 12. `ACCESS_BLOCKED` format

Use this exact structure when evidence is unavailable:

```text
ACCESS_BLOCKED
Needed evidence: <specific file, endpoint, or service read>
Current access level: <R0/R1/R2/R3>
Why it matters: <decision it would support>
Smallest approval needed: <one narrowly scoped read>
Actions not taken: <launch/check/flush/write/external probe>
```

Continue with all safe lower-level evidence before reporting a block.

## 13. Diagnostic report template

```text
Scope:
Branch / commit:
Alert window (UTC):
Access level used:
Runtime started/stopped: No/Yes + reason
Local state read: No/Yes + exact files
HTTP calls made: None/list
External/production reads: None/list
Evidence side effects: None/list

Signal stream:
Owning system:
Observed evidence:
Strongest delivery proof:
Diagnosis:
What the evidence does not prove:
Known documentation/implementation drift:
ACCESS_BLOCKED items:
Recommended next approved read or separate change bundle:
```

## 14. Automation-forward contract

A future local analytics diagnostic utility should:

- parse selected JSON files directly without importing BUS Core runtime modules;
- default to no network, no loopback HTTP, and no writes;
- validate JSON before interpretation and fail visibly on malformed input;
- redact event IDs, timestamps not needed for the requested window, secrets, tokens, and business data;
- emit structured aggregate output with access level and side-effect declarations;
- distinguish current queue/dead-letter length from cumulative counters;
- never call update check, telemetry preference, telemetry flush, staging, startup, or migration code.
- never write telemetry fields through `/app/config` as a diagnostic shortcut.

A future static documentation validator should compare checked-in endpoint guards, telemetry constants, state paths, and dev-mode variable names against this runbook. These utilities are proposals until separately approved and implemented; their absence does not authorize improvised active probes.
