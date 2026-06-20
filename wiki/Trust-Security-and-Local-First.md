# Trust, Security, and Local-First

## Local-First Means

BUS Core remains usable on local infrastructure without BUS Pro, a hosted account, forced cloud dependency, or telemetry. On packaged Windows installs, business data and configuration live under `%LOCALAPPDATA%\BUSCore`; in Docker, the main database is normally under the operator-mounted `/data` directory.

BUS Core does not send inventory, recipe, customer, or finance data to a BUS Core cloud sync service because Core has no cloud sync service. Features you explicitly configure, such as update checks or supported external integrations, may make the network requests needed for those features.

## Local Access Controls

BUS Core uses session checks around protected app routes. A shop can remain in simple unclaimed local mode or claim the instance and use local user accounts and permissions. UI visibility is convenience; backend route and permission checks remain the authority.

This does not turn the default deployment into an internet-ready server. Keep the packaged app and default Docker Compose binding on loopback. Exposing it to a LAN or public interface requires operator action and stronger host, network, reverse-proxy, and access controls; that is outside the default supported posture.

## Writes and Restore Safety

Mutating operations use the app's session, permission, write-gate, and route-specific safeguards according to the current route. Restore is deliberately staged: upload/select, preview, then commit. Treat local filesystem access and administrator access as trusted boundaries.

## Updates and Downloads

Update checks are optional and non-blocking. A manual update stage requires a trusted signed manifest, verifies the declared ZIP hash and size when present, safely extracts it, and verifies the Windows executable's Authenticode publisher and pinned signer identity before it can become verified-ready. The update check itself remains read-only and retains unsigned-manifest compatibility for discovery, so do not describe every piece of update metadata as signed.

Use official project release locations and read [Updates and Releases](Updates-and-Releases.md). Core has no silent background auto-update or telemetry behavior.

## Your Responsibilities

Protect the host account, local files, backup passwords, and any network exposure you configure. Keep encrypted exports outside the machine when appropriate. Local-first control also means local responsibility.
