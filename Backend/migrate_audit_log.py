"""
Migration script: Create the provider_audit_log table.
Run this once to add the audit trail table to your database.
"""
import asyncio
from database import engine
from models import ProviderAuditLog

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(ProviderAuditLog.__table__.create, checkfirst=True)
    print("✅ provider_audit_log table created successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
