from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.logging import setup_logging, LoggingMiddleware
from backend.api.user_api.agent_api import agent_router
from backend.api.user_api.login_api import login_router
from backend.api.health_api import health_router
from backend.api.records_api import records_router
from backend.api.reports_api import reports_router
from backend.api.profile_api import profile_router
from backend.api.session_api import session_router
from backend.api.learning_api import learning_router
from backend.api.mastery_api import mastery_router
from backend.api.points_api.points_api import points_router
from backend.api.vip_api.vip_api import vip_router
from backend.api.admin_api.admin_user_api import admin_user_router
from backend.api.admin_api.admin_audit_api import admin_audit_router
from backend.api.admin_api.admin_question_api import admin_question_router
from backend.api.admin_api.admin_learning_api import admin_learning_router
from backend.api.admin_api.admin_dashboard_api import admin_dashboard_router
from backend.api.learning_summary_api import learning_summary_router
from backend.core.hooks import startup_event, shutdown_event
from backend.middleware.exception import register_exception_handlers

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app = FastAPI(
    debug=os.getenv("APP_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"},
    title="学生学情分析系统",
    openapi_url="/api",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(login_router)
app.include_router(health_router)
app.include_router(records_router)
app.include_router(reports_router)
app.include_router(profile_router)
app.include_router(session_router)
app.include_router(learning_router)
app.include_router(mastery_router)
app.include_router(points_router)
app.include_router(vip_router)
app.include_router(admin_user_router)
app.include_router(admin_audit_router)
app.include_router(admin_question_router)
app.include_router(admin_learning_router)
app.include_router(admin_dashboard_router)
app.include_router(learning_summary_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
