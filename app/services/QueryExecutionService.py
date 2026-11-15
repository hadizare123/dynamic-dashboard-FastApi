# app/services/QueryExecutionService.py
from sqlalchemy import create_engine, text
from app.models.sys_data_source import SysDataSource

class QueryExecutionService:
    def execute_query(self, db_meta, query_obj):
        """
        اجرای کوئری‌های بیزینسی روی دیتاسورس‌های هدف با پشتیبانی از Pool،
        احراز هویت استاندارد و تنظیمات Timeout امن برای PostgreSQL.
        """
        # ۱. پیدا کردن دیتاسورس مربوطه بر اساس source_id (منطبق با ساختار جاوا)
        source = db_meta.query(SysDataSource).filter(
            SysDataSource.source_id == query_obj.source_id
        ).first()

        if not source:
            raise Exception(f"DataSource with ID {query_obj.source_id} پیدا نشد!")

        if hasattr(source, "is_active") and not source.is_active:
            raise Exception(f"DataSource with ID {query_obj.source_id} غیرفعال است!")

        if not source.jdbc_url:
            raise Exception("مقدار jdbc_url برای این دیتاسورس خالی است!")

        if not source.username:
            raise Exception("نام کاربری (username) دیتاسورس خالی است!")

        # ۲. تبدیل فرمت JDBC به فرمت استاندارد SQLAlchemy
        # مثال: jdbc:postgresql://localhost:5432/sales_target_db -> postgresql://localhost:5432/sales_target_db
        db_url = source.jdbc_url.replace("jdbc:", "")

        # ۳. مدیریت و اعتبارسنجی Timeout
        timeout_seconds = getattr(query_obj, "timeout_seconds", None) or 15
        try:
            timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError):
            timeout_seconds = 15

        if timeout_seconds <= 0:
            timeout_seconds = 15

        timeout_ms = timeout_seconds * 1000

        # ۴. ساخت انجین اتصال با انتقال امن پسورد در connect_args
        engine = create_engine(
            db_url,
            connect_args={
                "user": source.username,
                "password": source.password_enc  # پسورد به صورت متن ساده (Plaintext)
            },
            pool_pre_ping=True,
            pool_size=getattr(source, "pool_min_idle", None) or 2,
            max_overflow=(getattr(source, "pool_max_size", None) or 10) - (getattr(source, "pool_min_idle", None) or 2)
        )

        try:
            # ۵. اجرای کوئری در بستر یک Transaction با SET LOCAL امن
            with engine.begin() as conn:
                # استفاده از مقدار امن‌سازی شده و تبدیل شده به عدد صحیح (جلوگیری از خطای syntax در PG)
                conn.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))

                # اجرای کوئری اصلی ویجت
                sql_text = query_obj.sql_text.strip()
                result = conn.execute(text(sql_text))

                # ۶. تبدیل نتایج به لیست دیکشنری برای استفاده در لایه‌های جلو
                return [dict(row._mapping) for row in result]

        finally:
            # آزادسازی منابع انجین موقت
            engine.dispose()
