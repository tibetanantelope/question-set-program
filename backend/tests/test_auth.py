from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from sqlalchemy.exc import IntegrityError

from backend.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)
from backend.services.login_service import login_service as login_service_module
from backend.services.login_service.login_service import LoginService


def test_password_is_hashed_and_verified():
    password = "student123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_contains_identity_and_expiration():
    token = create_access_token(
        {"user_id": 7, "username": "student7"},
        expires_delta=timedelta(minutes=5),
    )
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["user_id"] == 7
    assert payload["username"] == "student7"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_duplicate_username_is_rejected(monkeypatch):
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock()
    db.execute.return_value = result

    async def fake_get_db():
        yield db

    monkeypatch.setattr(login_service_module, "get_db", fake_get_db)
    response = await LoginService().register("student1", "student123")

    assert response["code"] == 400
    assert response["msg"] == "用户名已存在"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unique_constraint_race_returns_business_error(monkeypatch):
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    async def fake_get_db():
        yield db

    monkeypatch.setattr(login_service_module, "get_db", fake_get_db)
    response = await LoginService().register("student1", "student123")

    assert response["code"] == 400
    assert response["msg"] == "用户名已存在"
    db.rollback.assert_awaited_once()
