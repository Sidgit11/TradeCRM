"""AI Insights API — deal-actionable nudges for entities.

Generates insights on-demand with a 24-hour in-memory cache per entity.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId
from app.agents.insights_agent import generate_insights
from app.schemas.insights import InsightsResponse, InsightItem

logger = get_logger("api.insights")
router = APIRouter(prefix="/insights", tags=["insights"])

# In-memory cache: {(tenant_id, entity_type, entity_id): (insights, generated_at)}
_cache: Dict[Tuple[str, str, str], Tuple[list, datetime]] = {}
CACHE_TTL = timedelta(hours=24)


def _get_cached(tenant_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID) -> Optional[Tuple[list, datetime]]:
    key = (str(tenant_id), entity_type, str(entity_id))
    if key in _cache:
        insights, generated_at = _cache[key]
        if datetime.now(timezone.utc) - generated_at < CACHE_TTL:
            return insights, generated_at
        del _cache[key]
    return None


def _set_cache(tenant_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, insights: list) -> datetime:
    key = (str(tenant_id), entity_type, str(entity_id))
    now = datetime.now(timezone.utc)
    _cache[key] = (insights, now)
    return now


def _invalidate_cache(tenant_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID):
    key = (str(tenant_id), entity_type, str(entity_id))
    _cache.pop(key, None)


VALID_ENTITY_TYPES = {"company", "contact", "opportunity", "lead"}


@router.get("/{entity_type}/{entity_id}", response_model=InsightsResponse)
async def get_insights(
    entity_type: str,
    entity_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    refresh: bool = False,
):
    """Get AI-generated actionable insights for an entity.

    Returns cached insights if available (24h TTL).
    Pass ?refresh=true to force regeneration.
    """
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}")

    # Check cache first
    if not refresh:
        cached = _get_cached(tenant_id, entity_type, entity_id)
        if cached:
            insights, generated_at = cached
            return InsightsResponse(
                entity_type=entity_type,
                entity_id=str(entity_id),
                insights=[InsightItem(**i) for i in insights],
                generated_at=generated_at.isoformat(),
                cached=True,
            )

    # Generate fresh insights
    try:
        raw_insights = await generate_insights(db, tenant_id, entity_type, entity_id)
    except Exception as e:
        logger.error("Insight generation failed: entity=%s/%s error=%s", entity_type, str(entity_id)[:8], str(e), exc_info=True)
        raw_insights = []

    generated_at = _set_cache(tenant_id, entity_type, entity_id, raw_insights)

    logger.info("insights: generated %d for %s/%s", len(raw_insights), entity_type, str(entity_id)[:8])

    return InsightsResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        insights=[InsightItem(**i) for i in raw_insights],
        generated_at=generated_at.isoformat(),
        cached=False,
    )


@router.post("/{entity_type}/{entity_id}/refresh", response_model=InsightsResponse)
async def refresh_insights(
    entity_type: str,
    entity_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Force-refresh insights for an entity (invalidates cache)."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}")

    _invalidate_cache(tenant_id, entity_type, entity_id)

    try:
        raw_insights = await generate_insights(db, tenant_id, entity_type, entity_id)
    except Exception as e:
        logger.error("Insight refresh failed: entity=%s/%s error=%s", entity_type, str(entity_id)[:8], str(e), exc_info=True)
        raw_insights = []

    generated_at = _set_cache(tenant_id, entity_type, entity_id, raw_insights)

    return InsightsResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        insights=[InsightItem(**i) for i in raw_insights],
        generated_at=generated_at.isoformat(),
        cached=False,
    )
