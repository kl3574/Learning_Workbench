"""HTTP trust boundary and non-reflective errors."""

import logging
import sqlite3
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from packages.contracts.canonical import strict_json

from ..config import Settings
from ..database import Database
from ..errors import ApiError, error_response
from ..security import authenticate, check_csrf

logger = logging.getLogger("learning_workbench.api")


def install_boundary(application: FastAPI, settings: Settings, database: Database) -> None:
    @application.middleware("http")
    async def local_request_boundary(request: Request, call_next: Any) -> Response:
        request.state.request_id = f"request_{uuid4().hex}"
        try:
            if len(request.headers.getlist("host")) != 1 or request.headers["host"] not in settings.allowed_hosts:
                raise ApiError(400, "HOST_DENIED", "请求的本机地址不受允许。")
            origins = request.headers.getlist("origin")
            if len(origins) > 1 or (origins and origins[0] not in settings.allowed_origins):
                raise ApiError(403, "ORIGIN_DENIED", "请求来源不受允许。")
            unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
            if unsafe and not origins:
                raise ApiError(403, "ORIGIN_DENIED", "写入请求必须来自已配置的本机页面。")
            bootstrap = request.url.path == "/api/v1/session/bootstrap" and request.method == "POST"
            if request.url.path.startswith("/api/v1/") and not bootstrap:
                request.state.identity = authenticate(database, request)
                if unsafe:
                    check_csrf(request, request.state.identity)
            if unsafe:
                # An authenticated import has its own finite file budget; ordinary
                # JSON mutations retain the smaller existing request limit.
                upload = request.method == "POST" and request.url.path == "/api/v1/imports"
                body_limit = settings.max_upload_bytes + 65536 if upload else settings.max_request_bytes
                declared_length = request.headers.get("content-length")
                if declared_length and (not declared_length.isdecimal() or int(declared_length) > body_limit):
                    raise ApiError(413, "REQUEST_TOO_LARGE", "请求超过本机接口大小限制。")
                chunks: list[bytes] = []
                total = 0
                async for chunk in request.stream():
                    total += len(chunk)
                    if total > body_limit:
                        raise ApiError(413, "REQUEST_TOO_LARGE", "请求超过本机接口大小限制。")
                    chunks.append(chunk)
                # Starlette's cached request body is replayed to the downstream FastAPI request.
                request._body = b"".join(chunks)
                if request._body and request.headers.get("content-type", "").split(";", 1)[0] == "application/json":
                    try:
                        strict_json(request._body.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        raise ApiError(422, "SCHEMA_INVALID", "JSON 编码、字段唯一性或数值格式不符合规范。") from None
            response = await call_next(request)
        except ApiError as error:
            response = error_response(request, error)
        except sqlite3.OperationalError:
            response = error_response(request, ApiError(503, "DATABASE_UNAVAILABLE", "本机存储暂不可用。", retryable=True))
        except Exception:
            logger.error("request_failed request_id=%s", request.state.request_id)
            response = error_response(request, ApiError(500, "INTERNAL_ERROR", "请求未能完成；请保留请求编号以便诊断。"))
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @application.exception_handler(ApiError)
    async def handle_domain_error(request: Request, error: ApiError) -> JSONResponse:
        return error_response(request, error)

    @application.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(request, ApiError(422, "SCHEMA_INVALID", "请求字段或字段值不符合接口规范。"))

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
        codes = {404: "REFERENCE_MISSING", 405: "METHOD_NOT_ALLOWED"}
        return error_response(request, ApiError(error.status_code, codes.get(error.status_code, "REQUEST_REJECTED"), "请求的资源或操作不可用。"))
