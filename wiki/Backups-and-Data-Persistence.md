# Backup and Restore

BUS Core is local-first, so the operator is responsible for protecting local business data. Make a backup before Start Fresh, restore, major host changes, or container recreation.

## Create an Encrypted Export

1. Open **Settings > Administration > Backup Export**.
2. Enter a non-empty backup password.
3. Select **Export**.
4. Confirm the new file appears under available exports.
5. Store the password separately and appropriately for your shop.

On Windows, exports are stored under `%LOCALAPPDATA%\BUSCore\exports` as encrypted `.db.gcm` files. The export is password-based AES-GCM; losing the password can make the backup unusable.

## Restore: Preview, Then Commit

1. Open **Settings > Administration > Restore (Preview then Commit)**.
2. Select a backup file or an available export and enter its password.
3. Select **Preview**. Preview validates the container and schema and shows table counts without replacing the active database.
4. Review the result and path.
5. Select **Commit (archives journals)** only when you intend to replace the active database.
6. Restart BUS Core when the UI reports that restart is required.

Commit enters maintenance mode, replaces database state through the guarded restore path, archives existing journals, and recreates empty journals. It is not an undo button. Keep the source export until you have verified the restored shop.

## Windows Path Note

v1.3.2 fixed export, preview, and restore handling for Windows paths containing spaces or `#`. Use the in-app staged upload/preview flow rather than moving database files by hand.

## Docker Persistence

The default container database is `/data/app.db` with `BUS_DB=/data/app.db`. Mount `/data` to durable host storage and verify the mount survives container recreation. SQLite may use active WAL/SHM sidecar files; do not copy or discard live database files casually. Prefer the in-app encrypted export.

## Safety Boundaries

- Preview before every commit.
- Do not treat a filename in the export list as proof that you know its password or that an off-device copy exists.
- Test restore in an appropriate environment before depending on a backup plan.
- A local export on the same failing disk is not a complete disaster-recovery strategy.
- BUS Core Self-Managed does not provide hosted backup or cloud sync; the operator owns backup and recovery. The upcoming, not-yet-generally-available TGC Managed BUS service is intended to add managed backup and recovery around the same portable BUS Core foundation.

Next: [Trust, Security, and Local-First](Trust-Security-and-Local-First.md).
