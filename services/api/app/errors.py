"""Uniform errors contain static messages, never rejected bodies or exception text."""

from fastapi import Request
from fastapi.responses import JSONResponse

from packages.contracts.domain_models import ErrorDetail, ErrorEnvelope

from .application.errors import ApiError as ApiError


def error_response(request: Request, error: ApiError) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=error.code,
            message=error.message,
            request_id=request.state.request_id,
            retryable=error.retryable,
            details=[],
        )
    )
    return JSONResponse(status_code=error.status, content=envelope.model_dump())
