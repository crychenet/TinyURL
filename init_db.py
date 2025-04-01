import asyncio
from db import engine
from models import Base
from models import User


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
