import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL from .env, or default to a local postgres instance
# Example: postgresql+asyncpg://user:password@localhost:5432/healthcare
DATABASE_URL = os.getenv("DATABASE_URL")

# Set echo=True to see all SQL queries (useful for debugging)
# Set echo=False for cleaner terminal output in production
engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    # Helper to create tables for development
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
