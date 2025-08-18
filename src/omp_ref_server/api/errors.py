from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field


class OMPError(BaseModel):
    code: str = Field(..., description="Stable machine-readable code")
    message: str = Field(..., description="Human-readable explanation")
    status: int = Field(..., description="HTTP status code duplicated here for convenience")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional diagnostic details")

    @staticmethod
    def code_for_status(status: int) -> str:
        return {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "unprocessable_entity",
            429: "rate_limited",
            500: "internal_error",
            503: "unavailable",
        }.get(status, "error")


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Error"
    details = exc.detail if isinstance(exc.detail, dict) else None
    ompe = OMPError(
        code=OMPError.code_for_status(exc.status_code),
        message=message,
        status=exc.status_code,
        details=details,
    )
    return JSONResponse({"error": ompe.model_dump()}, status_code=exc.status_code)


def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Normalize FastAPI/Pydantic 422 into 400 with consistent shape
    ompe = OMPError(
        code="bad_request",
        message="Invalid request",
        status=400,
        details={"errors": exc.errors()},
    )
    return JSONResponse({"error": ompe.model_dump()}, status_code=400)
