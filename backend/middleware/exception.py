"""Global exception handlers producing a stable JSON error contract."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger

logger = get_logger(__name__)


def _error(code: str, message: str, status_code: int, data=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "data": data},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError):
        return _error(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        return _error(
            "VALIDATION_ERROR",
            "请求参数不符合要求",
            422,
            data=jsonable_encoder({"errors": exc.errors()}),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
        response = _error(f"HTTP_{exc.status_code}", detail, exc.status_code)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError):
        original = getattr(exc, "orig", None)
        original_args = getattr(original, "args", ())
        mysql_error_code = original_args[0] if original_args else None
        if mysql_error_code in {1054, 1146}:
            logger.exception(
                "Database schema outdated on %s %s", request.method, request.url.path
            )
            return _error(
                "DATABASE_SCHEMA_OUTDATED",
                "数据库结构未升级，请按顺序执行缺失的 database SQL 脚本",
                503,
            )
        logger.exception("Database unavailable on %s %s", request.method, request.url.path)
        return _error(
            "DATABASE_UNAVAILABLE",
            "数据库暂时无法连接，请检查数据库服务或稍后重试",
            503,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error("INTERNAL_ERROR", "系统内部错误，请稍后重试", 500)
