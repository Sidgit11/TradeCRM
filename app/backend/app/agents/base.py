"""Base agent infrastructure — task runner, step tracking, WebSocket event emission."""
from typing import Any, Callable, Dict, List, Optional
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.activity import AgentTask, ActivityLog
from app.models.enums import AgentTaskStatus, AgentTaskType, ActorType

logger = get_logger("agents.base")


class AgentStepTracker:
    """Tracks agent progress through named steps, emitting updates."""

    def __init__(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        on_step_update: Optional[Callable] = None,
        on_narrative_update: Optional[Callable] = None,
    ):
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.steps: List[Dict[str, Any]] = []
        self.current_index = 0
        self._on_step_update = on_step_update
        self._on_narrative_update = on_narrative_update

    def define_steps(self, step_names: List[str]) -> None:
        self.steps = [
            {
                "name": name,
                "status": "pending",
                "detail": None,
                "started_at": None,
                "completed_at": None,
            }
            for name in step_names
        ]

    async def start_step(self, detail: Optional[str] = None) -> None:
        if self.current_index >= len(self.steps):
            return
        step = self.steps[self.current_index]
        step["status"] = "active"
        step["detail"] = detail
        step["started_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Agent step started: task=%s step=%s detail=%s",
            str(self.task_id)[:8], step["name"], detail,
        )
        if self._on_step_update:
            await self._on_step_update(self.tenant_id, self.task_id, self.steps, self.current_index)

    async def complete_step(self, detail: Optional[str] = None) -> None:
        if self.current_index >= len(self.steps):
            return
        step = self.steps[self.current_index]
        step["status"] = "completed"
        if detail:
            step["detail"] = detail
        step["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Agent step completed: task=%s step=%s",
            str(self.task_id)[:8], step["name"],
        )
        if self._on_step_update:
            await self._on_step_update(self.tenant_id, self.task_id, self.steps, self.current_index)
        self.current_index += 1

    async def fail_step(self, error: str) -> None:
        if self.current_index >= len(self.steps):
            return
        step = self.steps[self.current_index]
        step["status"] = "failed"
        step["detail"] = error
        step["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.error(
            "Agent step failed: task=%s step=%s error=%s",
            str(self.task_id)[:8], step["name"], error,
        )
        if self._on_step_update:
            await self._on_step_update(self.tenant_id, self.task_id, self.steps, self.current_index)

    async def update_narrative(self, text: str) -> None:
        if self._on_narrative_update:
            await self._on_narrative_update(self.tenant_id, self.task_id, text)


async def create_agent_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    task_type: AgentTaskType,
    input_data: Dict[str, Any],
) -> AgentTask:
    """Create an agent task record in the database."""
    task = AgentTask(
        tenant_id=tenant_id,
        task_type=task_type,
        status=AgentTaskStatus.pending,
        input_data=input_data,
        steps=[],
        current_step_index=0,
        created_by=user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info("Agent task created: id=%s type=%s tenant=%s", task.id, task_type.value, tenant_id)
    return task


async def update_agent_task(
    db: AsyncSession,
    task: AgentTask,
    status: Optional[AgentTaskStatus] = None,
    steps: Optional[List[Dict]] = None,
    current_step_index: Optional[int] = None,
    output_data: Optional[Dict] = None,
    error: Optional[str] = None,
    credits_consumed: Optional[int] = None,
) -> None:
    """Update an agent task's state."""
    if status:
        task.status = status
    if steps is not None:
        task.steps = steps
    if current_step_index is not None:
        task.current_step_index = current_step_index
    if output_data is not None:
        task.output_data = output_data
    if error is not None:
        task.error = error
    if credits_consumed is not None:
        task.credits_consumed = credits_consumed
    if status in (AgentTaskStatus.completed, AgentTaskStatus.failed):
        task.completed_at = datetime.now(timezone.utc)

    await db.commit()


async def log_activity(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor_type: ActorType,
    actor_id: Optional[uuid.UUID],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    detail: Optional[Dict] = None,
) -> None:
    """Log an activity event."""
    entry = ActivityLog(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    await db.commit()
