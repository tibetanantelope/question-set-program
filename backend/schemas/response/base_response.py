"""Unified response envelope for new business APIs."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "success"
    data: T | None = None


def success(data: Any = None, message: str = "success") -> dict:
    return {"code": "OK", "message": message, "data": data}
