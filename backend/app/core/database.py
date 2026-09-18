from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

database_url = settings.get_database_url()

if database_url.startswith("sqlite+aiosqlite"):
    engine = create_async_engine(database_url, echo=settings.DEBUG, connect_args={"check_same_thread": False})
else:
    engine = create_async_engine(database_url, echo=settings.DEBUG, pool_pre_ping=True)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
