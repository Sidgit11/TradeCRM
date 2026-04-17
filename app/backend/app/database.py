import ssl
import uuid
from datetime import datetime

from sqlalchemy import DateTime, event, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("database")

# Build connect_args for Neon SSL
connect_args = {}
if "neon.tech" in settings.DATABASE_URL or "ssl=require" in settings.DATABASE_URL:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context
    logger.info("SSL enabled for Neon database connection")

# Strip unsupported params from asyncpg URL
db_url = settings.DATABASE_URL.replace("?ssl=require", "").replace("&ssl=require", "")
# Also strip channel_binding which asyncpg doesn't support via URL
db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")
# Clean up any dangling ? or &
if db_url.endswith("?"):
    db_url = db_url[:-1]

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("DB connection checked out from pool")


@event.listens_for(engine.sync_engine, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    logger.debug("DB connection returned to pool")


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
