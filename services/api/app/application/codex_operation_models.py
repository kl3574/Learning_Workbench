"""Versioned memory-operation facts; v1 denied callback records stay unchanged."""
from typing import Annotated, Literal
from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexApprovalControl, CodexCommandOperation, CodexLocalToolBudget, SafeCode
from .codex_approval_models import SyntheticOperationCallback, ApprovalDecided, ApprovalClosed
from .codex_operation_profile import LiteralOperationClosure, LiteralOperationResult
from .provider_models import DispatchLease


class SupportedOperation(dm.StrictModel):
    version: Literal['codex-supported-memory-operation-v1']
    workspace_id: dm.Id
    approval_id: dm.Id
    actor_session_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    job_input_sha256: dm.Sha256
    dispatch_id: dm.Id
    execution_owner_id: dm.Id
    lease: DispatchLease
    profile_sha256: dm.Sha256
    input_proof_sha256: dm.Sha256
    request_sha256: dm.Sha256
    callback_json: Annotated[str, Field(min_length=2, max_length=131072, repr=False)]
    callback_sha256: dm.Sha256
    callback: SyntheticOperationCallback
    tools: CodexLocalToolBudget
    operation: CodexCommandOperation
    closure: LiteralOperationClosure
    created_at: dm.UTC
    expires_at: dm.UTC


class SupportedCreated(dm.StrictModel):
    kind: Literal['created']
    operation: SupportedOperation


class OperationStarted(dm.StrictModel):
    kind: Literal['started']
    execution_owner_id: dm.Id
    lease: DispatchLease
    operation_sha256: dm.Sha256
    budget_ordinal: Annotated[int, Field(strict=True, ge=1, le=32)]


class OperationFinished(dm.StrictModel):
    kind: Literal['finished']
    outcome: Literal['completed', 'failed', 'unknown']
    result: LiteralOperationResult | None
    error_code: SafeCode | None


class OperationEnvelope(dm.StrictModel):
    version: Literal['codex-generic-approval-event-v2']
    workspace_id: dm.Id
    approval_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: Annotated[SupportedCreated | ApprovalDecided | ApprovalClosed | OperationStarted | OperationFinished, Field(discriminator='kind')]


class TurnOperationBound(dm.StrictModel):
    kind: Literal['approval_operation_bound']
    turn_id: dm.Id
    approval_seq: dm.Revision
    approval_sha256: dm.Sha256
    control: CodexApprovalControl


class OperationControlEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v5']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnOperationBound
