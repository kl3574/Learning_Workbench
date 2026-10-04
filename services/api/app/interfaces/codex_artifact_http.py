"""Explicit selected artifact re-import; no HTTP scan or blob registration."""
from fastapi import APIRouter, Depends, Request
from pydantic import TypeAdapter
from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json
from ..application.codex_artifact_imports import CodexArtifactImports
from ..application.errors import ApiError
from ..codex_turn_dto import CodexArtifactImportView, CodexArtifactImportWrite
from .codex_bootstrap_http import no_control_body
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER


async def reject_duplicate_selection(request: Request):
    # Preserve the declared closed DTO/OpenAPI. A well-formed duplicated ID is
    # the norm's explicit 409 selection conflict; other shape errors stay 422.
    try:
        raw = strict_json(await request.body())
        if isinstance(raw, dict) and isinstance(raw.get('artifact_ids'), list):
            values = TypeAdapter(list[dm.Id]).validate_python(raw['artifact_ids'])
            if len(values) != len(set(values)):
                raise ApiError(409, 'CODEX_ARTIFACT_REJECTED', '本次选择含重复产物。')
    except (ValueError, TypeError, RecursionError):
        return


def create_codex_artifact_router(service: CodexArtifactImports) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[Depends(current_identity),
        Depends(unique_control_headers), Depends(private_response), Depends(query_fields())])

    @router.post('/sessions/{id}/artifacts/import', response_model=dm.JobRef, status_code=202,
        dependencies=[Depends(verify_write), Depends(reject_duplicate_selection)],
        openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(id: dm.Id, body: CodexArtifactImportWrite, request: Request) -> dm.JobRef:
        return service.create(request.state.identity, id, body, command_key(request))

    @router.get('/artifact-imports/{job_id}', response_model=CodexArtifactImportView,
        dependencies=[Depends(no_control_body)])
    def read(job_id: dm.Id, request: Request) -> CodexArtifactImportView:
        return service.read(request.state.identity, job_id)

    return router
