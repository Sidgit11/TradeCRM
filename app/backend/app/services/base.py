from typing import Optional

import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base
from app.logging_config import get_logger

logger = get_logger("services.base")

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def _scoped_query(self, tenant_id: uuid.UUID) -> Select:
        return select(self.model).where(self.model.tenant_id == tenant_id)

    async def create(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        data = obj_in.model_dump()
        data["tenant_id"] = tenant_id
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info(
            "Created %s id=%s tenant=%s",
            self.model.__tablename__, db_obj.id, tenant_id,
        )
        return db_obj

    async def get_by_id(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        obj_id: uuid.UUID,
    ) -> Optional[ModelType]:
        result = await db.execute(
            self._scoped_query(tenant_id).where(self.model.id == obj_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            logger.debug(
                "%s id=%s not found for tenant=%s",
                self.model.__tablename__, obj_id, tenant_id,
            )
        return obj

    async def get_multi(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 25,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        filters: Optional[dict[str, Any]] = None,
    ) -> tuple[list[ModelType], int]:
        query = self._scoped_query(tenant_id)

        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted.is_(False))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        if sort_by and hasattr(self.model, sort_by):
            order_fn = desc if sort_order == "desc" else asc
            query = query.order_by(order_fn(getattr(self.model, sort_by)))
        else:
            query = query.order_by(desc(self.model.created_at))

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())

        logger.debug(
            "Listed %s: tenant=%s count=%d total=%d skip=%d limit=%d",
            self.model.__tablename__, tenant_id, len(items), total, skip, limit,
        )
        return items, total

    async def update(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        obj_id: uuid.UUID,
        obj_in: UpdateSchemaType,
    ) -> Optional[ModelType]:
        db_obj = await self.get_by_id(db, tenant_id, obj_id)
        if db_obj is None:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        logger.info(
            "Updated %s id=%s tenant=%s fields=%s",
            self.model.__tablename__, obj_id, tenant_id, list(update_data.keys()),
        )
        return db_obj

    async def soft_delete(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        obj_id: uuid.UUID,
    ) -> bool:
        db_obj = await self.get_by_id(db, tenant_id, obj_id)
        if db_obj is None:
            return False

        if hasattr(db_obj, "is_deleted"):
            db_obj.is_deleted = True
            await db.commit()
            logger.info(
                "Soft-deleted %s id=%s tenant=%s",
                self.model.__tablename__, obj_id, tenant_id,
            )
            return True

        await db.delete(db_obj)
        await db.commit()
        logger.info(
            "Hard-deleted %s id=%s tenant=%s",
            self.model.__tablename__, obj_id, tenant_id,
        )
        return True
