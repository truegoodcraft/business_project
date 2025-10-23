from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from .provider import _is_under_root, _norm, _same_drive


def _normalize(path: str) -> str:
    return _norm(path)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _append_suffix(path: Path, index: int) -> Path:
    if index <= 0:
        return path
    stem = path.stem
    suffix = path.suffix
    return path.with_name(f"{stem}-{index}{suffix}")


def resolve_collision_append_1(target: Path) -> Path:
    candidate = target
    counter = 0
    while candidate.exists():
        counter += 1
        candidate = _append_suffix(target, counter)
    return candidate


def _quarantine_base(roots: Iterable[str]) -> Optional[Path]:
    first = next(iter(roots), None)
    if not first:
        return None
    base = Path(first)
    documents = base if base.name.lower() == "documents" else base / "Documents"
    return documents / "Quarantine"


@dataclass
class CollisionResult:
    resolved_path: Path
    collided: bool


class LocalFSExecutor:
    """Helper responsible for performing file-system mutations under local roots."""

    def __init__(self, allowed_roots: Iterable[str]):
        self._allowed_roots = [Path(r) for r in allowed_roots]
        self._allowed_norm = [_normalize(str(r)) for r in self._allowed_roots]
        base = _quarantine_base(self._allowed_norm)
        self._quarantine_move = (
            (base / "MoveSource") if base is not None else Path("data/quarantine/MoveSource")
        )
        self._quarantine_duplicates = (
            (base / "Duplicates") if base is not None else Path("data/quarantine/Duplicates")
        )
        self._quarantine_combined = (
            (base / "Combined") if base is not None else Path("data/quarantine/Combined")
        )

    # region policies
    def is_allowed(self, path: Path) -> bool:
        candidate = _normalize(str(path))
        for root in self._allowed_norm:
            if _is_under_root(candidate, root):
                return True
        return False

    def ensure_allowed(self, path: Path) -> None:
        if not self.is_allowed(path):
            raise PermissionError(f"Path {path} not under allowed roots")

    # endregion

    def collision_resolve(self, path: Path, mode: str = "append-1") -> CollisionResult:
        if mode != "append-1":
            return CollisionResult(resolved_path=path, collided=False)
        if not path.exists():
            return CollisionResult(resolved_path=path, collided=False)
        resolved = resolve_collision_append_1(path)
        return CollisionResult(resolved_path=resolved, collided=True)

    def _same_drive(self, a: Path, b: Path) -> bool:
        return _same_drive(str(a), str(b))

    def same_drive(self, a: Path, b: Path) -> bool:
        return self._same_drive(a, b)

    # rename/move helpers
    def _prepare_target(self, target: Path) -> None:
        _ensure_dir(target.parent)

    def _copy(self, src: Path, dest: Path) -> None:
        if src.is_dir():
            if dest.exists():
                raise FileExistsError(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

    def _move(self, src: Path, dest: Path) -> None:
        if src.is_dir():
            shutil.move(str(src), str(dest))
        else:
            os.replace(src, dest)

    def rename_or_move(
        self,
        src: Path,
        dest: Path,
        *,
        collision_mode: str = "append-1",
        quarantine: bool = True,
    ) -> Tuple[Path, Dict[str, str]]:
        self.ensure_allowed(src)
        self.ensure_allowed(dest)
        if not src.exists():
            raise FileNotFoundError(src)

        collision = self.collision_resolve(dest, collision_mode)
        final_dest = collision.resolved_path
        self._prepare_target(final_dest)

        metadata: Dict[str, str] = {}
        if self._same_drive(src, final_dest):
            if src.is_dir():
                shutil.move(str(src), str(final_dest))
            else:
                os.replace(src, final_dest)
            rollback_src = final_dest
            rollback_dest = src
            metadata["rollback"] = json.dumps({
                "op": "move",
                "src": str(rollback_src),
                "dest": str(rollback_dest),
            })
            return final_dest, metadata

        # cross-drive move: copy then quarantine original
        temp_name = final_dest.parent / f".__tgc_tmp_{uuid.uuid4().hex}{final_dest.suffix}"
        self._copy(src, temp_name)
        if final_dest.exists():
            os.replace(temp_name, final_dest)
        else:
            os.replace(temp_name, final_dest)
        rollback_steps = [
            {"op": "move", "src": str(final_dest), "dest": str(src)},
        ]
        if quarantine:
            q_target = self._quarantine_move / src.name
            _ensure_dir(q_target.parent)
            unique = q_target
            counter = 0
            while unique.exists():
                counter += 1
                unique = q_target.with_name(f"{q_target.stem}-{counter}{q_target.suffix}")
            shutil.move(str(src), str(unique))
            rollback_steps.append({"op": "move", "src": str(unique), "dest": str(src)})
            metadata["quarantine"] = str(unique)
        metadata["rollback"] = json.dumps(rollback_steps)
        return final_dest, metadata


__all__ = ["LocalFSExecutor", "resolve_collision_append_1"]
