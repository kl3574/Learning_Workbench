"""Strict upload and import-query projections; all effects live in the service."""

from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Header, Request, Response

from packages.contracts import domain_models as dm

from ..config import Settings
from ..application.jobs import JobService
from ..errors import ApiError
from ..import_dto import (
    ImportUpload, ImportStaged, ImportPreview, ImportCommitRequest, ImportCommitResponse,
    ImportCancelRequest, ImportCancelResponse, JobSnapshot, JobCancelRequest,
    SourceResponse, ImportDraftSnapshot,
)
from .http import current_identity, reject_query_fields, verify_write

if TYPE_CHECKING:
    from ..application.imports import ImportService

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


async def strict_upload_fields(request: Request) -> None:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        raise ApiError(422, "SCHEMA_INVALID", "导入需要 multipart 文件上传。")
    form = await request.form()
    keys = [key for key, _ in form.multi_items()]
    if len(keys) != len(set(keys)) or set(keys) - {"file", "kind", "target_course_id"}:
        raise ApiError(422, "SCHEMA_INVALID", "上传字段未知或重复。")


def create_import_router(settings: Settings, service: "ImportService") -> APIRouter:
    jobs = JobService(service.database)
    router = APIRouter(prefix="/api/v1", tags=["imports"],
                       dependencies=[Depends(current_identity), Depends(reject_query_fields)])

    @router.post("/imports", status_code=202, response_model=ImportStaged,
                 dependencies=[Depends(verify_write), Depends(strict_upload_fields)])
    async def stage(request: Request, upload: Annotated[ImportUpload, File()], idempotency_key: IdempotencyKey):
        try:
            data = await upload.file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise ApiError(413, "IMPORT_TOO_LARGE", "原件超过导入大小限制。")
            return service.stage(request.state.identity, data=data, filename=upload.file.filename or "upload",
                                 kind=upload.kind, target_course_id=upload.target_course_id, key=idempotency_key)
        finally:
            await upload.file.close()

    @router.get("/imports/{id}", response_model=ImportPreview)
    def preview(id: dm.Id, request: Request):
        return service.preview(request.state.identity, id)

    @router.post("/imports/{id}/commit", response_model=ImportCommitResponse, dependencies=[Depends(verify_write)])
    def commit(id: dm.Id, body: ImportCommitRequest, request: Request, idempotency_key: IdempotencyKey):
        return service.commit(request.state.identity, id, body, idempotency_key)

    @router.post("/imports/{id}/cancel", response_model=ImportCancelResponse, dependencies=[Depends(verify_write)])
    def cancel(id: dm.Id, body: ImportCancelRequest, request: Request, idempotency_key: IdempotencyKey):
        return service.cancel(request.state.identity, id, body, idempotency_key)

    @router.get("/jobs/{id}", response_model=JobSnapshot)
    def job(id: dm.Id, request: Request):
        return jobs.job(request.state.identity, id)

    @router.post("/jobs/{id}/cancel", response_model=JobSnapshot, dependencies=[Depends(verify_write)])
    def cancel_job(id: dm.Id, body: JobCancelRequest, request: Request, idempotency_key: IdempotencyKey):
        return jobs.cancel(request.state.identity, id, body, idempotency_key)

    @router.get("/drafts/{id}", response_model=ImportDraftSnapshot)
    def draft(id: dm.Id, request: Request):
        return service.draft(request.state.identity, id)

    @router.get("/sources/{id}", response_model=SourceResponse)
    def source(id: dm.Id, request: Request):
        return service.source(request.state.identity, id)

    @router.get("/artifacts/{id}/download", response_class=Response,
                responses={200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
                                 "headers": {"ETag": {"schema": {"type": "string"}}, "Content-Disposition": {"schema": {"type": "string"}}}}})
    def download(id: dm.Id, request: Request) -> Response:
        data, artifact = service.download(request.state.identity, id)
        disposition = "attachment; filename=download; filename*=UTF-8''" + quote(artifact.filename, safe="")
        return Response(data, media_type="application/octet-stream", headers={
            "Content-Disposition": disposition, "ETag": f'"{artifact.sha256}"',
        })

    return router
