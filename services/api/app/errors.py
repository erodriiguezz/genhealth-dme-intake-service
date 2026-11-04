import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

UNIQUE_VIOLATION = "23505"


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def envelope(
    status_code: int, code: str, message: str, details: Any = None, headers: dict | None = None
) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "details": details}},
        status_code=status_code,
        headers=headers,
    )


def constraint_name(exc: IntegrityError) -> str:
    """Only the constraint name. str(exc) carries Postgres DETAIL, which includes the row's PHI."""
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None) or "unknown"


def sqlstate(exc: IntegrityError) -> str | None:
    return getattr(exc.orig, "sqlstate", None)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return envelope(exc.status_code, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "unauthorized", 404: "not_found", 405: "method_not_allowed"}
        return envelope(
            exc.status_code,
            codes.get(exc.status_code, "http_error"),
            str(exc.detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only loc and msg: pydantic's `input` and `ctx` would echo submitted values.
        details = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return envelope(422, "validation_error", "Request validation failed.", details)

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        log.error("integrity error: constraint=%s", constraint_name(exc))
        if sqlstate(exc) == UNIQUE_VIOLATION:
            return envelope(409, "conflict", "Resource already exists.")
        return envelope(422, "constraint_violation", "Request violates a data constraint.")
