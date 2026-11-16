from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.dashboard_meta import SysDashboardQuery
from app.models.sys_data_source import SysDataSource
from app.Directory.database import get_db

router = APIRouter(prefix="/api/admin/dashboard/queries", tags=["Dashboard Queries"])


# ---------- Schemas ----------
class SourceResponse(BaseModel):
    source_id: int
    source_key: str
    display_name: str
    db_type: Optional[str] = None
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class QuerySchema(BaseModel):
    source_id: int
    category_id: Optional[int] = None
    report_title: str
    description: Optional[str] = None
    sql_text: str
    chart_type: str
    is_active: bool = True


class QueryResponse(QuerySchema):
    query_id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- Endpoints ----------
@router.get("/sources", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    return db.query(SysDataSource).filter(SysDataSource.is_active.is_(True)).all()


@router.get("", response_model=List[QueryResponse])
def list_queries(db: Session = Depends(get_db)):
    return db.query(SysDashboardQuery).order_by(SysDashboardQuery.query_id.desc()).all()


@router.get("/{query_id}", response_model=QueryResponse)
def get_query(query_id: int, db: Session = Depends(get_db)):
    db_query = db.query(SysDashboardQuery).filter(
        SysDashboardQuery.query_id == query_id
    ).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    return db_query


@router.post("", response_model=QueryResponse)
def create_query(query: QuerySchema, db: Session = Depends(get_db)):
    # تبدیل اسکیما به دیکشنری (بدون فیلد created_at چون در اسکیما نیست)
    db_query = SysDashboardQuery(**query.model_dump())
    try:
        db.add(db_query)
        db.commit()
        db.refresh(db_query)
    except Exception as e:
        db.rollback()
        # برگرداندن ارور شفاف به فرانت
        raise HTTPException(status_code=500, detail=f"Database Insert Error: {str(e)}")
    return db_query

@router.put("/{query_id}", response_model=QueryResponse)
def update_query(query_id: int, query: QuerySchema, db: Session = Depends(get_db)):
    db_query = db.query(SysDashboardQuery).filter(SysDashboardQuery.query_id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")

    # بروزرسانی فیلدها با snake_case
    for key, value in query.model_dump().items():
        setattr(db_query, key, value)

    try:
        db.commit()
        db.refresh(db_query)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Update Error: {str(e)}")
    return db_query


@router.delete("/{query_id}")
def delete_query(query_id: int, db: Session = Depends(get_db)):
    db_query = db.query(SysDashboardQuery).filter(
        SysDashboardQuery.query_id == query_id
    ).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    try:
        db.delete(db_query)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
    return {"ok": True, "deleted_query_id": query_id}
