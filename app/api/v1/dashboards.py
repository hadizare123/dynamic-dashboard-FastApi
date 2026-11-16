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
        "sortOrder": w.sort_order,
        "isVisible": getattr(w, "is_visible", None) or getattr(w, "isVisible", None),
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

    widgets = (
        db.query(SysDashboardWidget)
        .filter(SysDashboardWidget.dashboard_id == dashboard_id)
        .order_by(SysDashboardWidget.sort_order.asc())
        .all()
    )

    query_service = QueryExecutionService()
    widgets_response = []

    for widget in widgets:
        w_res = {
            "widget": _serialize_widget(widget),
            "data": [],
            "columns": [],
            "status": "OK",
        }

        if not widget.query_id:
            w_res["status"] = "NO_QUERY"
        else:
            query_obj = (
                db.query(SysDashboardQuery)
                .filter(SysDashboardQuery.query_id == widget.query_id)
                .first()
            )
            if not query_obj:
                w_res["status"] = "NO_QUERY"
            elif not getattr(query_obj, "is_active", True):
                w_res["status"] = "INACTIVE"
            else:
                try:
                    results = query_service.execute_query(db, query_obj)
                    w_res["data"] = results
                    w_res["columns"] = list(results[0].keys()) if results else []
                except Exception as e:
                    w_res["status"] = "ERROR"
                    w_res["error"] = str(e)

        widgets_response.append(w_res)

    return {"dashboard": _serialize_dashboard(dashboard), "widgets": widgets_response}


