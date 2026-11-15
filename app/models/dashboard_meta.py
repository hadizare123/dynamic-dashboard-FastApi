from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SysDashboard(Base):
    __tablename__ = "sys_dashboards"
    __table_args__ = {"schema": "dashboard_meta"}

    dashboard_id = Column(Integer, primary_key=True)
    dashboard_code = Column(String(50), nullable=False, unique=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    icon_name = Column(String(50), default="ph-squares-four")
    layout_type = Column(String(50), default="GRID")
    refresh_rate_sec = Column(Integer, default=0)
    theme_config = Column(Text, default='{"bg": "#17151C", "accent": "#AAA2B3", "card_bg": "#292531"}')
    is_public = Column(Boolean, default=True)
    created_by = Column(String(100), default="admin")
    # اصلاح شده:
    created_at = Column("created_at", DateTime, server_default=func.now())
    updated_at = Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now())

class SysDashboardWidget(Base):
    __tablename__ = "sys_dashboard_widgets"
    __table_args__ = {"schema": "dashboard_meta"}

    widget_id = Column(Integer, primary_key=True)
    dashboard_id = Column(Integer, nullable=False)
    query_id = Column(Integer, nullable=False)
    widget_title = Column(String(150))
    widget_type = Column(String(50), nullable=False)
    grid_pos_x = Column(Integer, default=0)
    grid_pos_y = Column(Integer, default=0)
    grid_width = Column(Integer, default=6)
    grid_height = Column(Integer, default=4)
    widget_props = Column(Text, default="{}")
    sort_order = Column(Integer, default=0)
    is_visible = Column("is_visible", Boolean, default=True)
    # اصلاح شده:
    created_at = Column("created_at", DateTime, server_default=func.now())

class SysDashboardQuery(Base):
    __tablename__ = "sys_dashboard_queries"
    __table_args__ = {"schema": "dashboard_meta"}

    query_id = Column(Integer, primary_key=True)
    category_id = Column(Integer)
    source_id = Column(Integer, nullable=False)
    report_title = Column(String(255), nullable=False)
    description = Column(Text)
    sql_text = Column(Text, nullable=False)
    chart_type = Column(String(50), default="TABLE")
    is_active = Column("is_active", Boolean, default=True)
    # اصلاح شده:
    created_at = Column("created_at", DateTime, server_default=func.now())
