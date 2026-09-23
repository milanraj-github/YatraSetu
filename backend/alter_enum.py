import asyncio
from app.core.database import async_session_maker
from sqlalchemy import text

async def alter_enum():
    async with async_session_maker() as session:
        try:
            await session.execute(text("ALTER TYPE emergencystatus ADD VALUE 'POTENTIAL';"))
            await session.execute(text("ALTER TYPE emergencystatus ADD VALUE 'ESCALATED';"))
            await session.execute(text("ALTER TYPE emergencystatus ADD VALUE 'DRIVER_CONFIRMED_SAFE';"))
            await session.commit()
            print("Altered Enum in Postgres")
        except Exception as e:
            print("Could not alter Enum (maybe already exists, or using SQLite):", e)
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(alter_enum())
