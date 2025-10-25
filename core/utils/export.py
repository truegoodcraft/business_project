"""Utilities for encrypted export and import of the BUS Core database."""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import tempfile
import time
from hashlib import pbkdf2_hmac, sha256
from pathlib import Path
from typing import Dict, Tuple

try:
    from argon2 import low_level as argon2_low_level
    from argon2.exceptions import Argon2Error
except Exception:  # pragma: no cover - argon2 optional
    argon2_low_level = None  # type: ignore[assignment]
    Argon2Error = Exception  # type: ignore[assignment]

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BUS_ROOT = Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
APP_DB = BUS_ROOT / "app.db"
APP_DIR = BUS_ROOT / "app"
DATA_DIR = APP_DIR / "data"
JOURNAL_DIR = DATA_DIR / "journals"
EXPORTS_DIR = BUS_ROOT / "exports"
for _p in (JOURNAL_DIR, EXPORTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

_DEFAULT_KDF = {
    "type": "argon2id",
    "time_cost": 3,
    "memory_kib": 65536,
    "parallelism": 1,
    "dklen": 32,
}

_PBKDF2_FALLBACK = {
    "type": "pbkdf2",
    "iterations": 600_000,
    "dklen": 32,
}

_AAD = b"TGCv05"


def _derive_key(password: str, salt: bytes, kdf_cfg: Dict[str, int | str] | None) -> bytes:
    if not password:
        raise ValueError("password_required")
    cfg_base: Dict[str, int | str] = dict(_DEFAULT_KDF)
    if kdf_cfg:
        cfg_base.update(kdf_cfg)
    kdf_type = str(cfg_base.get("type", "argon2id")).lower()
    if kdf_type == "argon2":
        kdf_type = "argon2id"
    cfg_base["type"] = "argon2id" if kdf_type.startswith("argon2") else kdf_type
    dklen = int(cfg_base.get("dklen", 32))
    password_bytes = password.encode("utf-8")

    if kdf_type == "argon2id" and argon2_low_level is not None:
        time_cost = int(cfg_base.get("time_cost", 3))
        memory_kib = int(cfg_base.get("memory_kib", 65536))
        parallelism = int(cfg_base.get("parallelism", 1))
        try:
            key = argon2_low_level.hash_secret_raw(
                password_bytes,
                salt,
                time_cost=time_cost,
                memory_cost=memory_kib,
                parallelism=parallelism,
                hash_len=dklen,
                type=argon2_low_level.Type.ID,
            )
            if kdf_cfg is not None:
                kdf_cfg.clear()
                kdf_cfg.update(cfg_base)
                kdf_cfg["type"] = "argon2id"
            return key
        except Argon2Error:
            pass

    if kdf_type == "pbkdf2":
        cfg_base.setdefault("iterations", _PBKDF2_FALLBACK["iterations"])
        cfg_base.setdefault("dklen", _PBKDF2_FALLBACK["dklen"])
    else:
        cfg_base = dict(_PBKDF2_FALLBACK)

    iterations = int(cfg_base.get("iterations", _PBKDF2_FALLBACK["iterations"]))
    dklen = int(cfg_base.get("dklen", 32))
    if kdf_cfg is not None:
        kdf_cfg.clear()
        kdf_cfg.update(cfg_base)
    return pbkdf2_hmac("sha256", password_bytes, salt, iterations, dklen=dklen)


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


def _count_rows(db_path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {"vendors": 0, "items": 0, "tasks": 0, "attachments": 0}
    if not db_path.exists():
        return counts
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        for table in counts.keys():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row = cursor.fetchone()
                counts[table] = int(row[0]) if row else 0
            except sqlite3.Error:
                counts[table] = 0
        cursor.close()
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
        kdf_cfg = dict(_DEFAULT_KDF)
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
            "kdf": kdf_cfg,
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
        if tmp_path.exists():
            for _ in range(5):
                try:
                    tmp_path.unlink()
                    break
                except PermissionError:
                    time.sleep(0.1)
                except Exception:
                    break


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
    except ValueError as exc:
        if str(exc) == "password_required":
            raise
        raise ValueError("decrypt_failed") from exc
    except Exception as exc:  # pragma: no cover - cryptography errors
        raise ValueError("decrypt_failed") from exc

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
        if tmp_path.exists():
            tmp_path.unlink()
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

    fd, tmp_db_path_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp_db_path = Path(tmp_db_path_str)
    try:
        tmp_db_path.write_bytes(plaintext)
        preview_counts = _count_rows(tmp_db_path)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = APP_DB.with_name(f"app.db.{timestamp}.bak")
        if APP_DB.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(APP_DB) as src, sqlite3.connect(backup_path) as dst:
                src.backup(dst)
        else:
            backup_path = None

        APP_DB.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_db_path, APP_DB)

        audit_path = JOURNAL_DIR / "plugin_audit.jsonl"
        audit_entry = {
            "ts": int(time.time()),
            "action": "import",
            "src": str(Path(path).resolve()),
            "manifest": container.get("manifest"),
            "preview_counts": preview_counts,
        }
        with audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(audit_entry, separators=(",", ":")) + "\n")
    finally:
        if tmp_db_path.exists():
            tmp_db_path.unlink()

    result: Dict[str, object] = {"ok": True, "replaced": True}
    if backup_path is not None:
        result["backup"] = str(backup_path)
    else:
        result["backup"] = None
    return result
