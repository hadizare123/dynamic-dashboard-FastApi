# محتویات فایل app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# یادت باشد پسورد دیتابیست را اینجا چک کنی
DATABASE_URL = "postgresql://postgres:cdq74CN2@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # پاک‌سازی تراکنش خراب
        raise
    finally:
        db.close()