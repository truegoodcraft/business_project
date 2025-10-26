"""Utilities for encrypted export and import of the BUS Core database."""
from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import tempfile
import time
from hashlib import sha256
from pathlib import Path
from typing import Dict, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BUS_ROOT = Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
APP_DB = BUS_ROOT / "app.db"
APP_DIR = BUS_ROOT / "app"
DATA_DIR = APP_DIR / "data"
JOURNAL_DIR = DATA_DIR / "journals"
EXPORTS_DIR = BUS_ROOT / "exports"
for _p in (JOURNAL_DIR, EXPORTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

_AAD = b"TGCv05"


def _derive_key(password: str, salt: bytes, kdf_cfg: dict) -> bytes:
    pw = password.encode("utf-8")
    t = (kdf_cfg or {}).get("type", "auto").lower()
    if t == "argon2id":
        try:
            from argon2.low_level import hash_secret_raw, Type
        except Exception as e:
            # explicit type requested but unavailable -> fail
            raise e
        return hash_secret_raw(
            pw,
            salt,
            time_cost=int(kdf_cfg.get("time_cost", 3)),
            memory_cost=int(kdf_cfg.get("memory_kib", 65536)),
            parallelism=int(kdf_cfg.get("parallelism", 1)),
            hash_len=int(kdf_cfg.get("dklen", 32)),
            type=Type.ID,
        )
    elif t == "pbkdf2":
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=int(kdf_cfg.get("dklen", 32)),
            salt=salt,
            iterations=int(kdf_cfg.get("iterations", 600000)),
        )
        return kdf.derive(pw)
    else:  # auto
        try:
            from argon2.low_level import hash_secret_raw, Type
            return hash_secret_raw(
                pw, salt, time_cost=3, memory_cost=65536,
                parallelism=1, hash_len=32, type=Type.ID,
            )
        except Exception:
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
            return kdf.derive(pw)


def _aesgcm_encrypt(key: bytes, plaintext: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, _AAD)
    ciphertext, tag = ct_with_tag[:-16], ct_with_tag[-16:]
    return ciphertext, tag


def _aesgcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext + tag, _AAD)


def _sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def _connect_readonly(db_path: Path):
    # Prefer immutable read-only; fallback to plain ro
    uri1 = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
    try:
        return sqlite3.connect(uri1, uri=True)
    except sqlite3.Error:
        uri2 = f"file:{db_path.as_posix()}?mode=ro"
        return sqlite3.connect(uri2, uri=True)


def _count_rows(db_path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {"vendors": 0, "items": 0, "tasks": 0, "attachments": 0}
    if not db_path.exists():
        return counts
    with _connect_readonly(db_path) as con:
        cur = con.cursor()
        for t in counts.keys():
            try:
                cur.execute(f"SELECT COUNT(1) FROM {t}")
                row = cur.fetchone()
                counts[t] = int(row[0]) if row else 0
            except sqlite3.Error:
                counts[t] = 0
    return counts


def _safe_under(root: Path, target: Path) -> bool:
    try:
        root_resolved = root.resolve()
        target_resolved = target.resolve()
    except FileNotFoundError:
        target_resolved = target.parent.resolve() / target.name
        root_resolved = root.resolve()
    try:
        common = os.path.commonpath([root_resolved, target_resolved])
    except ValueError:
        return False
    return Path(common) == root_resolved


def _retry_unlink(p: Path, attempts: int = 10, delay: float = 0.1):
    for _ in range(attempts):
        try:
            p.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(delay)


def _replace_with_retry(src: Path, dst: Path, attempts: int = 10, delay: float = 0.1):
    for _ in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(delay)
    os.replace(src, dst)


def export_db(password: str) -> Dict[str, object]:
    if not password:
        return {"ok": False, "error": "password_required"}
    if not APP_DB.exists():
        return {"ok": False, "error": "missing_db"}

    fd, tmp_name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with sqlite3.connect(str(APP_DB)) as source, sqlite3.connect(tmp_name) as dest:
            source.backup(dest)
        plaintext = tmp_path.read_bytes()
        row_counts = _count_rows(tmp_path)
        db_hash = _sha256_hex(plaintext)

        salt = os.urandom(16)
        nonce = os.urandom(12)
        # Decide KDF by availability
        try:
            import importlib

            importlib.import_module("argon2.low_level")
            kdf_cfg = {
                "type": "argon2id",
                "time_cost": 3,
                "memory_kib": 65536,
                "parallelism": 1,
                "dklen": 32,
            }
        except Exception:
            kdf_cfg = {
                "type": "pbkdf2",
                "iterations": 600000,
                "dklen": 32,
            }
        key = _derive_key(password, salt, kdf_cfg)
        ciphertext, tag = _aesgcm_encrypt(key, plaintext, nonce)

        container_manifest = {
            "version": "v0.5",
            "ts": int(time.time()),
            "row_counts": row_counts,
            "db_hash": db_hash,
        }
        container = {
            "magic": "TGCv05",
            "version": "v0.5",
            "kdf": {**kdf_cfg},
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "manifest": container_manifest,
        }

        ts = container_manifest["ts"]
        export_path = EXPORTS_DIR / f"TGC_EXPORT_{ts}.tgc"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=EXPORTS_DIR, delete=False) as tmp_file:
            tmp_json_path = Path(tmp_file.name)
            json.dump(container, tmp_file, separators=(",", ":"))
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_json_path, export_path)

        plain_buffer = bytearray(plaintext)
        for i in range(len(plain_buffer)):
            plain_buffer[i] = 0
        del plaintext

        return {"ok": True, "path": str(export_path), "manifest": container_manifest}
    finally:
        _retry_unlink(tmp_path)


def _load_and_decrypt(path: Path, password: str) -> Tuple[Dict[str, object], bytes]:
    if not password:
        raise ValueError("password_required")

    if not _safe_under(EXPORTS_DIR, path):
        raise PermissionError("path_out_of_roots")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("cannot_read_file")

    try:
        raw = path.read_text("utf-8")
        container = json.loads(raw)
    except Exception as exc:  # pragma: no cover - parse errors aggregated
        raise ValueError("bad_container") from exc

    try:
        if container.get("magic") != "TGCv05":
            raise ValueError
        salt = base64.b64decode(container["salt"])
        nonce = base64.b64decode(container["nonce"])
        tag = base64.b64decode(container["tag"])
        ciphertext = base64.b64decode(container["ciphertext"])
        kdf_cfg_obj = container.get("kdf")
        kdf_cfg = dict(kdf_cfg_obj) if isinstance(kdf_cfg_obj, dict) else None
    except Exception as exc:  # pragma: no cover - invalid structure
        raise ValueError("bad_container") from exc

    try:
        key = _derive_key(password, salt, kdf_cfg)
        plaintext = _aesgcm_decrypt(key, nonce, ciphertext, tag)
    except Exception:
        raise ValueError("decrypt_failed")

    return container, plaintext


def import_preview(path: str, password: str) -> Dict[str, object]:
    try:
        container, plaintext = _load_and_decrypt(Path(path), password)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        msg = str(exc)
        if msg not in {
            "path_out_of_roots",
            "cannot_read_file",
            "bad_container",
            "decrypt_failed",
            "password_required",
        }:
            msg = "bad_container"
        return {"ok": False, "error": msg}

    fd, tmp_path_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp_path = Path(tmp_path_str)
    try:
        tmp_path.write_bytes(plaintext)
        preview_counts = _count_rows(tmp_path)
    finally:
        _retry_unlink(tmp_path)
    incompatible = container.get("manifest", {}).get("version") != "v0.5"
    response: Dict[str, object] = {
        "ok": True,
        "preview": preview_counts,
        "incompatible": incompatible,
        "expected": "v0.5",
    }
    if incompatible:
        response["found"] = container.get("manifest", {}).get("version")
    return response


def import_commit(path: str, password: str) -> Dict[str, object]:
    try:
        container, plaintext = _load_and_decrypt(Path(path), password)
    except (PermissionError, FileNotFoundError, ValueError) as exc:
        msg = str(exc)
        if msg not in {
            "path_out_of_roots",
            "cannot_read_file",
            "bad_container",
            "decrypt_failed",
            "password_required",
        }:
            msg = "bad_container"
        return {"ok": False, "error": msg}

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(plaintext)
        tf.flush()
        os.fsync(tf.fileno())
        tmp_db_path = Path(tf.name)

    backup_path: Path | None = None
    try:
        ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        candidate_backup = APP_DB.with_suffix(f".db.{ts}.bak")

        APP_DB.parent.mkdir(parents=True, exist_ok=True)
        if APP_DB.exists():
            shutil.copy2(APP_DB, candidate_backup)
            backup_path = candidate_backup

        _replace_with_retry(tmp_db_path, APP_DB)

        audit_path = JOURNAL_DIR / "plugin_audit.jsonl"
        audit_entry = {
            "ts": int(time.time()),
            "action": "import",
            "src": str(Path(path).resolve()),
            "manifest": container.get("manifest"),
        }
        try:
            con = _connect_readonly(APP_DB)
        except NameError:
            con = sqlite3.connect(str(APP_DB))
        with con:
            audit_entry["preview_counts"] = {**_count_rows(APP_DB)}
        with audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(audit_entry, separators=(",", ":")) + "\n")
    finally:
        # Best-effort cleanup in case replace failed to remove the temp
        _retry_unlink(tmp_db_path)

    result: Dict[str, object] = {"ok": True, "replaced": True}
    if backup_path is not None:
        result["backup"] = str(backup_path)
    else:
        result["backup"] = None
    return result
