"""Auto-update action for pulling the latest repository changes."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class UpdateAction(SimpleAction):
    """Pull the latest changes from the tracked Git remote."""

    id: str = "U"
    name: str = "Update from repository"
    description: str = "Fetch and merge latest code"

    def build_plan(self, controller: Controller) -> str:  # noqa: D401 - simple delegation
        steps = [
            "Check for Git installation and repository status",
            "Record the Git remotes configured for this project",
            "Run `git pull --ff-only` from the project root",
            "Log stdout/stderr to the current run for traceability",
        ]
        warnings: List[str] = []
        remote_details: List[str] = []
        if not self._git_available():
            warnings.append("Git executable not found on PATH; install Git to enable auto-update.")
        if not self._is_git_repo():
            warnings.append("Current project directory is not a Git repository; skipping update.")
        else:
            if not self._has_remote():
                warnings.append("No Git remotes are configured; add a remote before attempting to update.")
            else:
                remote_details = self._remote_descriptions()
        notes = [
            "Dry-run mode only previews the command. Use Apply to perform the pull.",
            "If local changes conflict, resolve them manually after the pull attempt.",
        ]
        if remote_details:
            notes.append("Configured remotes:")
            notes.extend(f"  - {entry}" for entry in remote_details)
        return self.render_plan(self.name, steps, warnings=warnings or None, notes=notes)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        plan_text = controller.build_plan(self.id)
        repo_path = self._repo_root()
        if not self._git_available():
            error = "Git executable not available; cannot update automatically."
            context.log_notes("update_error", [error])
            return ActionResult(plan_text=plan_text, changes=[], errors=[error], notes=self._dry_run_message())
        if not self._is_git_repo():
            error = f"No Git repository detected at {repo_path}."
            context.log_notes("update_error", [error])
            return ActionResult(plan_text=plan_text, changes=[], errors=[error], notes=self._dry_run_message())
        if not self._has_remote():
            error = "No Git remotes are configured; cannot pull updates."
            context.log_notes("update_error", [error])
            context.log_notes("configured_remotes", ["Configured remotes: none"])
            return ActionResult(plan_text=plan_text, changes=[], errors=[error], notes=self._dry_run_message())

        command = ["git", "pull", "--ff-only"]
        remotes = self._remote_descriptions()
        if remotes:
            context.log_notes("configured_remotes", remotes)
        context.log_notes("update_command", ["Command: " + " ".join(command), f"Working directory: {repo_path}"])
        if not context.apply:
            preview = f"Would run: {' '.join(command)} in {repo_path}"
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview=preview,
            )

        completed = subprocess.run(
            command,
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
        stdout_lines = self._split_lines(completed.stdout)
        stderr_lines = self._split_lines(completed.stderr)
        if stdout_lines:
            context.log_notes("update_stdout", stdout_lines)
        if stderr_lines:
            context.log_notes("update_stderr", stderr_lines)

        if completed.returncode != 0:
            errors = [
                f"git pull exited with status {completed.returncode}",
            ]
            if stderr_lines:
                errors.append(stderr_lines[-1])
            return ActionResult(plan_text=plan_text, changes=[], errors=errors, notes=[])

        changes = stdout_lines or ["Repository already up to date."]
        notes = ["Repository updated successfully."]
        return ActionResult(plan_text=plan_text, changes=changes, errors=[], notes=notes)

    @staticmethod
    def _git_available() -> bool:
        return shutil.which("git") is not None

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[2]

    def _is_git_repo(self) -> bool:
        return (self._repo_root() / ".git").exists()

    def _has_remote(self) -> bool:
        return bool(self._remote_entries())

    def _remote_descriptions(self) -> List[str]:
        entries = self._remote_entries()
        if not entries:
            return []
        return entries

    def _remote_entries(self) -> List[str]:
        repo_path = self._repo_root()
        try:
            completed = subprocess.run(
                ["git", "remote", "-v"],
                cwd=repo_path,
                capture_output=True,
                check=False,
                text=True,
            )
        except FileNotFoundError:
            return []
        if completed.returncode != 0:
            return []
        entries: List[str] = []
        for line in completed.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) >= 3:
                name, url, kind = parts[0], parts[1], parts[2].strip("()")
                entry = f"{name} ({kind}) -> {url}"
            else:
                entry = stripped
            if entry not in entries:
                entries.append(entry)
        return entries

    @staticmethod
    def _split_lines(value: str | None) -> List[str]:
        if not value:
            return []
        return [line for line in value.splitlines() if line.strip()]
