import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.Directory.database import get_db
from app.models.dashboard_meta import SysDashboard, SysDashboardQuery, SysDashboardWidget
from app.services.QueryExecutionService import QueryExecutionService

router = APIRouter()

def _parse_json_object(value):
    if not isinstance(value, str): return value
    try: return json.loads(value)
    except (TypeError, ValueError): return value

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
        "createdAt": getattr(d, 'created_at', None) or getattr(d, 'createdAt', None),
        "updatedAt": getattr(d, 'updated_at', None) or getattr(d, 'updatedAt', None),
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
        "isVisible": getattr(w, 'is_visible', None) or getattr(w, 'isVisible', None),
        "createdAt": getattr(w, 'created_at', None) or getattr(w, 'createdAt', None),
    }

@router.get("/dashboards/{dashboard_id}")
def get_dashboard_full_details(dashboard_id: int, db: Session = Depends(get_db)):
    dashboard = db.query(SysDashboard).filter(SysDashboard.dashboard_id == dashboard_id).first()
    if not dashboard: raise HTTPException(status_code=404, detail="Dashboard not found")

    widgets = db.query(SysDashboardWidget).filter(SysDashboardWidget.dashboard_id == dashboard_id).order_by(SysDashboardWidget.sort_order.asc()).all()

    query_service = QueryExecutionService()
    widgets_response = []

    for widget in widgets:
        w_res = {
            "widget": _serialize_widget(widget),
            "data": [], "columns": [], "status": "OK"
        }

        if not widget.query_id:
            w_res["status"] = "NO_QUERY"
        else:
            query_obj = db.query(SysDashboardQuery).filter(SysDashboardQuery.query_id == widget.query_id).first()
            if not query_obj:
                w_res["status"] = "NO_QUERY"
            elif not getattr(query_obj, 'is_active', True):
                w_res["status"] = "INACTIVE"
            else:
                try:
                    results = query_service.execute_query(db, query_obj)
                    w_res["data"] = results
                    w_res["columns"] = list(results[0].keys()) if results else []
                except Exception as e:
                    w_res["status"] = "ERROR"; w_res["error"] = str(e)
        widgets_response.append(w_res)

    return {"dashboard": _serialize_dashboard(dashboard), "widgets": widgets_response}
@router.get("/dashboards/list")
def list_dashboards(db: Session = Depends(get_db)):
    dashboards = db.query(SysDashboard).order_by(SysDashboard.dashboard_id.asc()).all()
    return [
        {
            "dashboard_id": d.dashboard_id,
            "title": d.title,
            "dashboard_code": d.dashboard_code
        }
        for d in dashboards
    ]