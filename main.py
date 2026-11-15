from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.dashboards import router as dashboards_router
from app.api.v1.dashboard_queries import router as queries_router  # روتر جدیدی که ساختیم

app = FastAPI(title="Dynamic Dashboard API", version="1.0.0")

# حل مشکل CORS برای فرانت‌ند Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. ثبت روترهای داشبورد (بدون prefix)
app.include_router(dashboards_router)

# 2. ثبت روتر مدیریت کوئری‌ها (با prefix مشخص برای جدا شدن از سایر APIها)
app.include_router(queries_router)

@app.get("/")
def root():
    return {"message": "Python Backend is Running!"}
