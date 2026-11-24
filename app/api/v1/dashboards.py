import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.Directory.database import get_db
from app.models.dashboard_meta import SysDashboard, SysDashboardQuery, SysDashboardWidget
from app.services.QueryExecutionService import QueryExecutionService

router = APIRouter()


# ==========================================
# Pydantic Schemas
# ==========================================
class DashboardCreateRequest(BaseModel):
    dashboard_code: str = Field(..., min_length=1, max_length=50, description="کد یکتای داشبورد")
    title: str = Field(..., min_length=1, max_length=100, description="عنوان داشبورد")
    description: Optional[str] = None
    icon_name: Optional[str] = Field(default="ph-squares-four", max_length=50)
    layout_type: Optional[str] = Field(default="GRID", max_length=50)
    refresh_rate_sec: Optional[int] = Field(default=0, ge=0)
    theme_config: Optional[str] = None
    is_public: Optional[bool] = True
    created_by: Optional[str] = Field(default="admin", max_length=100)


class DashboardUpdateRequest(BaseModel):
    dashboard_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon_name: Optional[str] = Field(default=None, max_length=50)
    layout_type: str = Field(default="GRID", min_length=1, max_length=50)
    refresh_rate_sec: int = Field(default=0, ge=0)
    is_public: bool = True


# ==========================================
# Helpers / Serializers
# ==========================================
def _parse_json_object(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _serialize_dashboard(d):
    return {
        "dashboardId": d.dashboard_id,
        "dashboardCode": d.dashboard_code,
        "title": d.title,
        "description": d.description,
        "iconName": d.icon_name,
        "layoutType": d.layout_type,
        "refreshRateSec": d.refresh_rate_sec,
        "themeConfig": _parse_json_object(d.theme_config),
        "isPublic": d.is_public,
        "createdBy": d.created_by,
        "createdAt": getattr(d, "created_at", None) or getattr(d, "createdAt", None),
        "updatedAt": getattr(d, "updated_at", None) or getattr(d, "updatedAt", None),
    }


def _serialize_widget(w):
    return {
        "widgetId": w.widget_id,
        "dashboardId": w.dashboard_id,
        "queryId": w.query_id,
        "widgetTitle": w.widget_title,
        "widgetType": w.widget_type,
        "gridPosX": w.grid_pos_x,
        "gridPosY": w.grid_pos_y,
        "gridWidth": w.grid_width,
        "gridHeight": w.grid_height,
        "widgetProps": _parse_json_object(w.widget_props),
        "columnTitles": w.column_titles or {},
        "sortOrder": w.sort_order,
        "isVisible": w.is_visible,
        "createdAt": getattr(w, "created_at", None) or getattr(w, "createdAt", None),
    }


def _handle_create_dashboard(payload: DashboardCreateRequest, db: Session):
    clean_code = payload.dashboard_code.strip()
    clean_title = payload.title.strip()

    if not clean_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="کد داشبورد نمی‌تواند خالی باشد.",
        )
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="عنوان داشبورد نمی‌تواند خالی باشد.",
        )

    # بررسی تکراری نبودن کد قبل از insert
    existing = db.query(SysDashboard).filter(SysDashboard.dashboard_code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"داشبوردی با کد '{clean_code}' از قبل ثبت شده است.",
        )

    # مقداردهی به تم پیش‌فرض در صورت خالی بودن
    default_theme = '{"bg": "#17151C", "accent": "#AAA2B3", "card_bg": "#292531"}'
    theme_val = payload.theme_config if payload.theme_config else default_theme

    new_dashboard = SysDashboard(
        dashboard_code=clean_code,
        title=clean_title,
        description=payload.description,
        icon_name=payload.icon_name or "ph-squares-four",
        layout_type=payload.layout_type or "GRID",
        refresh_rate_sec=payload.refresh_rate_sec if payload.refresh_rate_sec is not None else 0,
        theme_config=theme_val,
        is_public=True if payload.is_public is None else payload.is_public,
        created_by=payload.created_by or "admin",
    )

    try:
        db.add(new_dashboard)
        db.commit()
        db.refresh(new_dashboard)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="کد داشبورد تکراری است.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطای پایگاه داده در ثبت داشبورد: {str(exc)}",
        )

    return _serialize_dashboard(new_dashboard)


# ==========================================
# Endpoints
# ==========================================

# هر دو مسیر پوشش داده شده‌اند تا اگر روتر با prefix="/dashboards" یا بدون پیشوند include شده باشد، 404 ندهد:
@router.post("/", status_code=status.HTTP_201_CREATED)
@router.post("/dashboards", status_code=status.HTTP_201_CREATED)
def create_dashboard_endpoint(payload: DashboardCreateRequest, db: Session = Depends(get_db)):
    return _handle_create_dashboard(payload, db)


@router.put("/dashboards/{dashboard_id}")
def update_dashboard_endpoint(
    dashboard_id: int, payload: DashboardUpdateRequest, db: Session = Depends(get_db)
):
    dashboard = db.query(SysDashboard).filter(SysDashboard.dashboard_id == dashboard_id).first()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    clean_code = payload.dashboard_code.strip()
    clean_title = payload.title.strip()
    if not clean_code or not clean_title:
        raise HTTPException(status_code=422, detail="کد و عنوان داشبورد نمی‌توانند خالی باشند.")

    duplicate = db.query(SysDashboard).filter(
        SysDashboard.dashboard_code == clean_code,
        SysDashboard.dashboard_id != dashboard_id,
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="کد داشبورد تکراری است.")

    changes = payload.model_dump(exclude_unset=True)
    changes.update(dashboard_code=clean_code, title=clean_title)
    for key, value in changes.items():
        setattr(dashboard, key, value)

    try:
        db.commit()
        db.refresh(dashboard)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="کد داشبورد تکراری است.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="خطا در ذخیره تغییرات داشبورد.")

    return _serialize_dashboard(dashboard)


@router.delete("/dashboards/{dashboard_id}")
def delete_dashboard_endpoint(dashboard_id: int, db: Session = Depends(get_db)):
    dashboard = db.query(SysDashboard).filter(SysDashboard.dashboard_id == dashboard_id).first()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="داشبورد پیدا نشد.")

    try:
        # Widgets belong to this dashboard; shared queries and data sources remain.
        db.query(SysDashboardWidget).filter(
            SysDashboardWidget.dashboard_id == dashboard_id
        ).delete(synchronize_session=False)
        db.delete(dashboard)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="داشبورد به اطلاعات دیگری وابسته است و حذف نشد.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="خطا در حذف داشبورد.")

    return {"ok": True, "deleted_dashboard_id": dashboard_id}


@router.get("/dashboards/list")
def list_dashboards(db: Session = Depends(get_db)):
    dashboards = (
        db.query(SysDashboard)
        .order_by(SysDashboard.dashboard_id.desc())
        .all()
    )

    return [
        {
            "dashboard_id": d.dashboard_id,
            "dashboard_code": d.dashboard_code,
            "title": d.title,
            "description": d.description,
            "layout_type": d.layout_type,
            "icon_name": d.icon_name,
            "refresh_rate_sec": d.refresh_rate_sec,
            "is_public": d.is_public,
        }
        for d in dashboards
    ]
@router.get("/dashboards/{dashboard_id}")
def get_dashboard_full_details(dashboard_id: int, db: Session = Depends(get_db)):
    dashboard = db.query(SysDashboard).filter(SysDashboard.dashboard_id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    widgets = db.query(SysDashboardWidget).filter(SysDashboardWidget.dashboard_id == dashboard_id).order_by(SysDashboardWidget.sort_order.asc()).all()

    query_service = QueryExecutionService()
    widgets_response = []

    for widget in widgets:
        w_res = {
            "widget": _serialize_widget(widget),
            "data": [],
            "columns": [],
            "status": "OK"
        }

        if widget.is_visible is False:
            w_res["status"] = "HIDDEN"
            widgets_response.append(w_res)
            continue

        if not widget.query_id:
            w_res["status"] = "NO_QUERY"
            widgets_response.append(w_res)
            continue

        try:
            # ⭐ مهم: خواندن کوئری و اجرای آن داخل یک try-except امن قرار گیرد
            query_obj = db.query(SysDashboardQuery).filter(SysDashboardQuery.query_id == widget.query_id).first()
            if not query_obj:
                w_res["status"] = "NO_QUERY"
            elif not getattr(query_obj, 'is_active', True):
                w_res["status"] = "INACTIVE"
            else:
                w_res["columns"], w_res["data"] = query_service.execute_query(db, query_obj)
        except Exception as e:
            # 🔴 هر خطایی داد (چه در lookup و چه در execute)، تراکنش فوری ریست شود
            db.rollback()
            import traceback
            traceback.print_exc()

            w_res["status"] = "ERROR"
            w_res["error"] = str(e)

        widgets_response.append(w_res)

    return {"dashboard": _serialize_dashboard(dashboard), "widgets": widgets_response}




# Widget administration uses the same router and database session as dashboards.
from typing import Literal
from pydantic import ConfigDict, field_validator, model_validator
from pydantic.alias_generators import to_camel


class WidgetWriteRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dashboard_id: int = Field(gt=0)
    query_id: int = Field(gt=0)
    widget_title: str = Field(min_length=1, max_length=150)
    widget_type: Literal['TABLE', 'KPI', 'CHART_BAR', 'CHART_LINE', 'CHART_PIE'] = 'TABLE'
    grid_pos_x: int = Field(default=0, ge=0, le=11)
    grid_pos_y: int = Field(default=0, ge=0)
    grid_width: int = Field(default=6, ge=1, le=12)
    grid_height: int = Field(default=4, ge=1)
    widget_props: dict = Field(default_factory=dict)
    column_titles: dict[str, str] = Field(default_factory=dict)
    sort_order: int = 0
    is_visible: bool = True

    @field_validator('widget_title')
    @classmethod
    def validate_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('عنوان ویجت نمی‌تواند خالی باشد.')
        return value

    @model_validator(mode='after')
    def validate_grid(self):
        if self.grid_pos_x + self.grid_width > 12:
            raise ValueError('موقعیت و عرض ویجت از ۱۲ ستون بیشتر است.')
        return self


def _widget_or_404(widget_id, db):
    widget = db.query(SysDashboardWidget).filter(SysDashboardWidget.widget_id == widget_id).first()
    if widget is None:
        raise HTTPException(status_code=404, detail='ویجت پیدا نشد.')
    return widget


def _widget_values(payload, db, existing=None):
    dashboard = db.query(SysDashboard).filter(SysDashboard.dashboard_id == payload.dashboard_id).first()
    if dashboard is None:
        raise HTTPException(status_code=422, detail='داشبورد انتخاب‌شده پیدا نشد.')
    query = db.query(SysDashboardQuery).filter(SysDashboardQuery.query_id == payload.query_id).first()
    if query is None:
        raise HTTPException(status_code=422, detail='کوئری انتخاب‌شده پیدا نشد.')
    if not query.is_active and (existing is None or existing.query_id != payload.query_id):
        raise HTTPException(status_code=422, detail='یک کوئری فعال انتخاب کنید.')
    values = payload.model_dump()
    if existing and 'column_titles' not in payload.model_fields_set and existing.query_id == payload.query_id:
        values.pop('column_titles')
    return values


def _commit_widget(db, widget=None):
    try:
        db.commit()
        if widget is not None:
            db.refresh(widget)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='عملیات به دلیل وابستگی اطلاعات انجام نشد.')
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail='خطا در ذخیره اطلاعات ویجت.')


@router.get('/api/admin/dashboard/widgets/dashboards')
def list_widget_dashboards(db: Session = Depends(get_db)):
    return list_dashboards(db)


@router.get('/api/admin/dashboard/widgets')
def list_widgets(db: Session = Depends(get_db)):
    widgets = db.query(SysDashboardWidget).order_by(SysDashboardWidget.widget_id.desc()).all()
    return [_serialize_widget(widget) for widget in widgets]


@router.post('/api/admin/dashboard/widgets', status_code=201)
def create_widget(payload: WidgetWriteRequest, db: Session = Depends(get_db)):
    widget = SysDashboardWidget(**_widget_values(payload, db))
    db.add(widget)
    _commit_widget(db, widget)
    return _serialize_widget(widget)


@router.put('/api/admin/dashboard/widgets/{widget_id}')
def update_widget(widget_id: int, payload: WidgetWriteRequest, db: Session = Depends(get_db)):
    widget = _widget_or_404(widget_id, db)
    for key, value in _widget_values(payload, db, existing=widget).items():
        setattr(widget, key, value)
    _commit_widget(db, widget)
    return _serialize_widget(widget)


@router.delete('/api/admin/dashboard/widgets/{widget_id}')
def delete_widget(widget_id: int, db: Session = Depends(get_db)):
    widget = _widget_or_404(widget_id, db)
    db.delete(widget)
    _commit_widget(db)
    return {'ok': True, 'deleted_widget_id': widget_id}
