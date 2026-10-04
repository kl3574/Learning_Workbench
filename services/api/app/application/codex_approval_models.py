"""Versioned original callback records; the v1 intake authorizes no tool.

The synthetic callback adapter has a local turn-ID mapping by definition. It is
not an app-server frame decoder or a claim about a host execution profile.
"""
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexApprovalControl, CodexDeniedOperation, CodexLocalToolBudget, GenericApprovalDecisionAck, SafeCode
from .provider_models import DispatchLease


class SyntheticOperationCallback(dm.StrictModel):
    version: Literal['codex-synthetic-operation-callback-v1']
    rpc_id: dm.Id
    thread_id: dm.Id
    turn_id: dm.Id
    item_id: dm.Id
    method: Literal['command/requestApproval', 'file/requestApproval', 'network/requestApproval']
    request_text: Annotated[str, Field(max_length=20000)]


class ApprovalOperation(dm.StrictModel):
    version: Literal['codex-unsupported-operation-v1']
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
    operation: CodexDeniedOperation
    created_at: dm.UTC
    expires_at: dm.UTC


class ApprovalCreated(dm.StrictModel):
    kind: Literal['created']
    operation: ApprovalOperation


class ApprovalCommand(dm.StrictModel):
    actor_session_id: dm.Id
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    body: dm.ApprovalDecision
    ack: GenericApprovalDecisionAck


class ApprovalDecided(dm.StrictModel):
    kind: Literal['decided']
    command: ApprovalCommand


class ApprovalClosed(dm.StrictModel):
    kind: Literal['closed']
    reason: SafeCode


class ApprovalEnvelope(dm.StrictModel):
    version: Literal['codex-generic-approval-event-v1']
    workspace_id: dm.Id
    approval_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: Annotated[ApprovalCreated | ApprovalDecided | ApprovalClosed, Field(discriminator='kind')]


class TurnApprovalBound(dm.StrictModel):
    kind: Literal['approval_bound']
    turn_id: dm.Id
    approval_seq: dm.Revision
    approval_sha256: dm.Sha256
    control: CodexApprovalControl


class ApprovalControlEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v3']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnApprovalBound
