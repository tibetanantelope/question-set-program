import os

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

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
