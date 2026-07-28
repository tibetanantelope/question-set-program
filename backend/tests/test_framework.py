import os

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import OperationalError

os.environ.setdefault(
    "SQL_DATABASE_URL",
    "mysql+asyncmy://test:test@127.0.0.1:3306/test",
)

from backend.core.exceptions import BusinessError
from backend.middleware.exception import register_exception_handlers


def test_business_error_uses_unified_response():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/failed")
    async def failed():
        raise BusinessError("INSUFFICIENT_POINTS", "积分不足", 400)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failed")

    assert response.status_code == 400
    assert response.json() == {
        "code": "INSUFFICIENT_POINTS",
        "message": "积分不足",
        "data": None,
    }


def test_http_exception_preserves_authenticate_header():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/protected")
    async def protected():
        raise HTTPException(
            status_code=401,
            detail="无效凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["message"] == "无效凭证"


def test_database_error_returns_service_unavailable_without_details():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/database")
    async def database():
        raise SQLAlchemyError("host and password must not reach the client")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/database")

    assert response.status_code == 503
    assert response.json() == {
        "code": "DATABASE_UNAVAILABLE",
        "message": "数据库暂时无法连接，请检查数据库服务或稍后重试",
        "data": None,
    }


def test_missing_database_column_reports_outdated_schema():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/database-schema")
    async def database_schema():
        original = Exception(1054, "Unknown column 'practice.answer_request_id'")
        raise OperationalError("SELECT practice.answer_request_id", {}, original)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/database-schema")

    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_SCHEMA_OUTDATED"
    assert "数据库结构未升级" in response.json()["message"]
