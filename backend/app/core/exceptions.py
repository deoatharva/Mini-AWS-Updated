import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Application error returned as a consistent JSON payload."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    def __init__(self, code: str = "not_found", message: str = "Resource not found.") -> None:
        super().__init__(404, code, message)


class ConflictError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(409, code, message)


class UnauthorizedError(AppError):
    def __init__(self, code: str = "authentication_required", message: str = "Sign in to continue.") -> None:
        super().__init__(401, code, message)


class ForbiddenError(AppError):
    def __init__(self, code: str = "forbidden", message: str = "You do not have access to this resource.") -> None:
        super().__init__(403, code, message)


class ValidationError(AppError):
    def __init__(self, code: str, message: str, details: object | None = None) -> None:
        super().__init__(422, code, message, details)


class ServiceUnavailableError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(503, code, message)


def _error_body(code: str, message: str, details: object | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ()) if part != "body"),
                "message": error.get("msg", "Invalid value."),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request validation failed.", details),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )
