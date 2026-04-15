import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.init_db import initialize_database
from db.cache import start_cache_updater

from api.routers.auth_router import router as auth_router
from api.routers.public import router as public_router
from api.routers.registration import router as registration_router
from api.routers.admin import router as admin_router
from api.routers.admin_references import router as admin_references_router

app = FastAPI(title="Muay Thai Tournament API", docs_url="/api/docs", openapi_url="/api/openapi.json")

allowed_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=bool(allowed_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(public_router, prefix="/api/public", tags=["public"])
app.include_router(registration_router, prefix="/api/registration", tags=["registration"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_references_router, prefix="/api/admin/references", tags=["admin-references"])

temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_files")
os.makedirs(temp_dir, exist_ok=True)

@app.on_event("startup")
def startup():
    initialize_database()
    start_cache_updater()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
