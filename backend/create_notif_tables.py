import asyncio
from app.core.database import engine
from app.models.base import Base
# import models
import app.models.user
import app.models.notification

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Created tables")

if __name__ == "__main__":
    asyncio.run(create_tables())
