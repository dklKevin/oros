"""
Database connection and session management for Biomedical Knowledge Platform.

Uses SQLAlchemy 2.0 async patterns with connection pooling.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""

    pass


# Global engine and session factory (initialized lazily)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """
    Get or create the async database engine.

    Args:
        settings: Optional settings override

    Returns:
        Configured async SQLAlchemy engine
    """
    global _engine

    if _engine is None:
        if settings is None:
            settings = get_settings()

        _engine = create_async_engine(
            settings.async_database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
            echo=settings.database_echo,
        )

        # Log pool events in debug mode
        if settings.is_development:
            from sqlalchemy.pool import PoolProxiedConnection
            from sqlalchemy.pool.base import ConnectionPoolEntry

            @event.listens_for(_engine.sync_engine, "checkout")
            def receive_checkout(
                dbapi_connection: Any,
                connection_record: ConnectionPoolEntry,
                connection_proxy: PoolProxiedConnection,
            ) -> None:
                logger.debug("connection_checkout", pool_size=_engine.pool.size())

            @event.listens_for(_engine.sync_engine, "checkin")
            def receive_checkin(
                dbapi_connection: Any,
                connection_record: ConnectionPoolEntry,
            ) -> None:
                logger.debug("connection_checkin", pool_size=_engine.pool.size())

    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.

    Args:
        settings: Optional settings override

    Returns:
        Configured async session factory
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get a database session.

    Yields:
        Database session that auto-closes after request

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def DatabaseSession() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of FastAPI.

    Yields:
        Database session that auto-closes

    Example:
        async with DatabaseSession() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(settings: Settings | None = None) -> None:
    """
    Initialize database connection and verify connectivity.

    Args:
        settings: Optional settings override
    """
    engine = get_engine(settings)
    async with engine.begin() as conn:
        # Verify connection
        await conn.execute(text("SELECT 1"))
        logger.info("database_connected", url=str(engine.url).split("@")[-1])

        # Verify pgvector extension
        result = await conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        if result.scalar() is None:
            logger.warning("pgvector_extension_missing")
        else:
            logger.info("pgvector_extension_verified")


async def close_db() -> None:
    """Close database connections and dispose of the engine."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("database_disconnected")
        _engine = None
        _session_factory = None


async def health_check() -> dict[str, Any]:
    """
    Perform database health check.

    Returns:
        Health check result with status and details.
        Note: Error details are logged but not exposed in response for security.
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

            # Get pool stats
            pool = engine.pool
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
    except Exception as e:
        # Log full error for debugging but don't expose to client
        logger.error("database_health_check_failed", error=str(e), exc_info=True)
        # Return generic error message to prevent information leakage
        return {
            "status": "unhealthy",
            "error": "Database connection failed. Check server logs for details.",
        }
