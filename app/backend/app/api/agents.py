"""API endpoints for triggering and monitoring agent tasks."""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.activity import AgentTask
from app.models.enums import AgentTaskStatus, AgentTaskType

logger = get_logger("api.agents")
router = APIRouter(prefix="/agents", tags=["agents"])


class RunAgentRequest(BaseModel):
    task_type: str
    input_data: dict = {}


class AgentTaskResponse(BaseModel):
    id: str
    task_type: str
    status: str
    steps: list
    current_step_index: int
    input_data: dict
    output_data: Optional[dict] = None
    error: Optional[str] = None
    credits_consumed: int
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


def _task_response(t: AgentTask) -> AgentTaskResponse:
    return AgentTaskResponse(
        id=str(t.id),
        task_type=t.task_type.value,
        status=t.status.value,
        steps=t.steps or [],
        current_step_index=t.current_step_index,
        input_data=t.input_data or {},
        output_data=t.output_data,
        error=t.error,
        credits_consumed=t.credits_consumed,
        created_at=t.created_at.isoformat(),
        completed_at=t.completed_at.isoformat() if t.completed_at else None,
    )


@router.post("/run", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED)
async def run_agent(
    body: RunAgentRequest,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an agent task. Returns the task record for status tracking."""
    # Validate task type
    try:
        task_type = AgentTaskType(body.task_type)
    except ValueError:
        valid = [t.value for t in AgentTaskType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_type. Must be one of: {valid}",
        )

    task = AgentTask(
        tenant_id=tenant_id,
        task_type=task_type,
        status=AgentTaskStatus.pending,
        input_data=body.input_data,
        steps=[],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info("Agent task queued: id=%s type=%s tenant=%s", task.id, task_type.value, tenant_id)

    # TODO: dispatch to Celery worker for async execution
    # For now, the task stays in "pending" — Phase 4 will wire up execution

    return _task_response(task)


@router.get("/tasks", response_model=list)
async def list_agent_tasks(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
):
    """List agent tasks for the current tenant."""
    query = select(AgentTask).where(AgentTask.tenant_id == tenant_id)

    if status_filter:
        query = query.where(AgentTask.status == status_filter)

    query = query.order_by(desc(AgentTask.created_at)).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [_task_response(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_agent_task(
    task_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific agent task with steps and results."""
    result = await db.execute(
        select(AgentTask).where(
            AgentTask.id == task_id,
            AgentTask.tenant_id == tenant_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return _task_response(task)
