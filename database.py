# database.py
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/eydb"

# 2. Create the Engine (The connection factory)
engine = create_engine(DATABASE_URL, echo=True) # echo=True prints SQL queries to console

# 3. Initialize DB (Run this on startup to create tables)
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# 4. The Dependency (The most important part)
def get_session() -> Generator:
    with Session(engine) as session:
        yield session
        # The session automatically closes here after the request finishes