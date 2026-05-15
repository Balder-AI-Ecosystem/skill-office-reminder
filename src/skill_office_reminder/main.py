from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any


def _is_core_repo(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "pyproject.toml").is_file() and (candidate / "ecosystem").is_dir()


def _candidate_core_repos() -> list[Path]:
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[2]
    candidates: list[Path] = []

    configured = str(os.getenv("AUTOBOT_CORE_REPO", "")).strip()
    if configured:
        candidates.append(Path(configured).expanduser())

    for anchor in (current_file.parent, Path.cwd().resolve()):
        candidates.extend([anchor, *anchor.parents])

    parent_dir = repo_root.parent
    if parent_dir.exists():
        candidates.extend(path for path in parent_dir.iterdir() if path.is_dir())

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _default_core_repo() -> Path:
    for candidate in _candidate_core_repos():
        if _is_core_repo(candidate):
            return candidate
    raise RuntimeError("Unable to locate the core repo. Set AUTOBOT_CORE_REPO to a valid core repo path.")


def _ensure_core_repo_on_path() -> Path:
    candidate = _default_core_repo()
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
    return candidate


_CORE_REPO = _ensure_core_repo_on_path()

from ecosystem.contracts import HealthSnapshot, TaskRequest, TaskResult  # noqa: E402
from ecosystem.skills import BaseSkill, SkillCapability, SkillManifest  # noqa: E402

if TYPE_CHECKING:
    from ecosystem.domains.office.module import OfficeAssistantModule


def _map_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"completed", "success", "ok"}:
        return "completed"
    if normalized in {"blocked", "needs_confirmation", "awaiting_confirmation"}:
        return "blocked"
    if normalized in {"preview", "dry_run"}:
        return "preview"
    return "failed"


class Skill(BaseSkill):
    def __init__(self, module: "OfficeAssistantModule" | None = None) -> None:
        self.module = module or self._build_module()

    @staticmethod
    def _build_module() -> "OfficeAssistantModule":
        from ecosystem.domains.office.module import OfficeAssistantModule

        return OfficeAssistantModule()

    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="skill-office-reminder",
            version="0.1.0",
            mode="local_plugin",
            entrypoint="src.skill_office_reminder.main:Skill",
            core_api=">=1.0,<2.0",
            capabilities=[
                SkillCapability(
                    id="office_reminder.create_reminder",
                    description="Preview or create an office reminder in the local reminder store.",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    risk_level="medium",
                    confirmation_required=True,
                    retry_policy="manual_review",
                    observability_events=["office_reminder.create_reminder"],
                ),
                SkillCapability(
                    id="office_reminder.list_reminders",
                    description="List saved office reminders from local storage.",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    retry_policy="bounded_backoff",
                    observability_events=["office_reminder.list_reminders"],
                ),
            ],
            permissions={
                "read_memory": False,
                "write_memory": False,
                "internet_access": False,
                "file_write": True,
                "external_actions": False,
            },
            healthcheck={"kind": "python", "target": "src.skill_office_reminder.main:healthcheck"},
            timeout_ms=60000,
            enabled_by_default=True,
        )

    def healthcheck(self) -> HealthSnapshot:
        snapshot = self.module.health_snapshot()
        return HealthSnapshot(
            status=snapshot.status,
            available=snapshot.available,
            updated_at=snapshot.updated_at,
            detail=snapshot.detail,
            counters=dict(snapshot.counters or {}),
            evidence=dict(snapshot.evidence or {}),
        )

    def execute(self, request: TaskRequest) -> TaskResult:
        handler = self._resolve_handler(request.capability)
        payload = handler(**dict(request.parameters or {}))
        return TaskResult(
            task_id=request.task_id,
            status=_map_status(payload.get("status")),
            detail=str(payload.get("detail") or payload.get("status") or "Skill execution finished."),
            failure_category=str(payload.get("failure_category") or "").strip() or None,
            artifacts={"result": payload},
            evidence={"bridge_mode": True},
            next_actions=list(payload.get("next_actions") or []),
            module_name="skill-office-reminder",
            capability=request.capability,
        )

    def _resolve_handler(self, capability: str):
        mapping = {
            "office_reminder.create_reminder": self.module.create_reminder,
            "office_reminder.list_reminders": self.module.list_reminders,
        }
        capability_name = str(capability or "").strip()
        if capability_name not in mapping:
            raise ValueError(f"Unsupported capability: {capability_name}")
        return mapping[capability_name]


def healthcheck() -> dict[str, Any]:
    return Skill().healthcheck().as_dict()