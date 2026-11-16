from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from sqlalchemy.orm import declarative_base

# تعریف Base مستقیماً همین‌جا (یا از جایی که تو پروژه‌ات تعریف شده import کن)
Base = declarative_base()

class SysDataSource(Base):
    __tablename__ = "sys_data_sources"
    __table_args__ = {"schema": "dashboard_meta"}

    source_id = Column(Integer, primary_key=True, index=True)
    source_key = Column(String(50), nullable=False, unique=True)
    code = Column(String(50))
    display_name = Column(String(100), nullable=False)
    db_type = Column(String(50), nullable=False)
    jdbc_url = Column(Text, nullable=False)
    username = Column(String(100))
    password_enc = Column(String(255)) # اصلاح شد: نام ستون در دیتابیس معمولاً password_enc است
    pool_min_idle = Column(Integer, default=2)
    pool_max_size = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
