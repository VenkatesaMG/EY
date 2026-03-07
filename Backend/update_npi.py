import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def change_npi(old_npi, new_npi):
    engine = create_async_engine("postgresql+asyncpg://postgres:password@localhost:5432/HealthCare")
    
    async with engine.begin() as conn:
        print(f"Checking for {old_npi}...")
        res = await conn.execute(text("SELECT * FROM providers_master_per WHERE npi = :npi"), {"npi": old_npi})
        row = res.fetchone()
        if not row:
            print("Row not found.")
            return
            
        print("Inserting new row...")
        cols = row._mapping.keys()
        
        insert_cols = []
        insert_vals = []
        params = {}
        for col in cols:
            insert_cols.append(col)
            insert_vals.append(f":{col}")
            val = row._mapping[col]
            if col == 'npi':
                val = new_npi
            elif isinstance(val, (dict, list)):
                val = json.dumps(val)
            params[col] = val
            
        await conn.execute(text(f"INSERT INTO providers_master_per ({','.join(insert_cols)}) VALUES ({','.join(insert_vals)})"), params)
        
        print("Updating child tables...")
        await conn.execute(text("UPDATE providers_master_prof SET npi = :new_npi WHERE npi = :old_npi"), {"new_npi": new_npi, "old_npi": old_npi})
        await conn.execute(text("UPDATE providers_master_meta SET npi = :new_npi WHERE npi = :old_npi"), {"new_npi": new_npi, "old_npi": old_npi})
        await conn.execute(text("UPDATE provider_audit_log SET npi = :new_npi WHERE npi = :old_npi"), {"new_npi": new_npi, "old_npi": old_npi})
        
        print("Deleting old row...")
        await conn.execute(text("DELETE FROM providers_master_per WHERE npi = :old_npi"), {"old_npi": old_npi})
        
        print("Done!")

if __name__ == '__main__':
    asyncio.run(change_npi("99999999999999999999", "111"))
