from enum import StrEnum
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail, ErrorResponse


class ErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    EVENT_NOT_OPEN = "EVENT_NOT_OPEN"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INVALID_SESSION_STATUS = "INVALID_SESSION_STATUS"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    QUESTIONS_NOT_COMPLETED = "QUESTIONS_NOT_COMPLETED"
    CARD_NOT_FOUND = "CARD_NOT_FOUND"
    REPLY_NOT_FOUND = "REPLY_NOT_FOUND"
    COMPLETION_CODE_NOT_FOUND = "COMPLETION_CODE_NOT_FOUND"
    COMPLETION_CODE_ALREADY_REDEEMED = "COMPLETION_CODE_ALREADY_REDEEMED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = str(code)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code = ErrorCode.BAD_REQUEST.value
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = ErrorCode.UNAUTHORIZED.value
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = ErrorCode.FORBIDDEN.value
    elif exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        code = ErrorCode.INTERNAL_ERROR.value

    response = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=str(exc.detail),
            details={},
        )
    )
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.BAD_REQUEST.value,
            message="요청이 올바르지 않습니다.",
            details={"errors": exc.errors()},
        )
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response.model_dump(),
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="서버 오류가 발생했습니다.",
            details={},
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(),
    )
