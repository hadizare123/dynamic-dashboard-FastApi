from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List, Any

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class SysDashboardSchema(CamelModel):
    dashboard_id: int
    dashboard_code: str
    title: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    layout_type: Optional[str] = None
    refresh_rate_sec: int
    is_public: bool
    # دقت کن: اینجا نام‌های دیتابیس (snake_case) رو می‌نویسیم
    # Pydantic خودش به camelCase تبدیلش می‌کنه در خروجی
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class SysDashboardWidgetSchema(CamelModel):
    widget_id: int
    widget_title: Optional[str] = None
    widget_type: str
    grid_pos_x: int
    grid_pos_y: int
    grid_width: int
    grid_height: int
    # اینجاست که معجزه اتفاق می‌افته:
    # اگر در مدل SQL اسمش is_visible هست، اینجا is_visible بنویس
    # ولی Pydantic خودش در JSON خروجی `isVisible` رو میده
    is_visible: bool

class WidgetDetailResponse(CamelModel):
    widget: SysDashboardWidgetSchema
    data: List[dict]
    columns: List[str]
    status: str
    error: Optional[str] = None
