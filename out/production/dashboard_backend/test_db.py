from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:cdq74CN2@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    print(result.fetchone())
