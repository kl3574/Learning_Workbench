"""Closed local-control transport from PRODUCT_DESIGN §20.16 (no tool grant)."""
from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BeforeValidator, ConfigDict, Field, model_validator

from packages.contracts import domain_models as dm


def _safe_label(value: str) -> str:
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ValueError('Unicode scalar text required') from None
    if (not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or value.startswith(('/', '\\')) or '\\' in value or '://' in value):
        raise ValueError('A nonblank safe control label is required')
    return value


def _false(value: object) -> object:
    if value is not False:
        raise ValueError('Only boolean false is supported')
    return value


def _two(value: object) -> object:
    if type(value) is not int or value != 2:
        raise ValueError('The original acknowledgement revision is 2')
    return value


SafeLabel = Annotated[str, Field(min_length=1, max_length=240), AfterValidator(_safe_label)]
EmptyActions = Annotated[list[str], Field(min_length=0, max_length=0)]
FalseOnly = Annotated[Literal[False], BeforeValidator(_false)]
RevisionTwo = Annotated[Literal[2], BeforeValidator(_two)]


class BootstrapModel(dm.StrictModel):
    model_config = ConfigDict(hide_input_in_errors=True)


class CodexBootstrapFeatures(BootstrapModel):
    approvals: FalseOnly
    interrupt: FalseOnly
    artifacts: FalseOnly


class CodexBootstrapPreparationWrite(BootstrapModel):
    sandbox_root_id: dm.Id
    allowed_actions: EmptyActions


class CodexBootstrapScope(BootstrapModel):
    version: Literal['codex-local-session-bootstrap-v1']
    sandbox_root_id: dm.Id
    sandbox_label: SafeLabel
    allowed_actions: EmptyActions
    adapter_version: SafeLabel
    bootstrap_profile_sha256: dm.Sha256


class CodexBootstrapPreparationView(BootstrapModel):
    id: dm.Id
    revision: dm.Revision
    actor_session_id: dm.Id
    status: Literal['pending', 'approved', 'declined', 'consumed']
    scope: CodexBootstrapScope
    operation_sha256: dm.Sha256
    created_at: dm.UTC
    expires_at: dm.UTC
    consent_id: dm.Id | None
    session_id: dm.Id | None
    validity: Literal['current', 'expired', 'changed', 'unavailable', 'closed']

    @model_validator(mode='after')
    def relationships(self) -> Self:
        if datetime.fromisoformat(self.expires_at) - datetime.fromisoformat(self.created_at) != timedelta(minutes=10):
            raise ValueError('The preparation lifetime must be ten minutes')
        revision = {'pending': 1, 'approved': 2, 'declined': 2, 'consumed': 3}[self.status]
        if self.revision != revision:
            raise ValueError('State and revision disagree')
        if (self.consent_id is not None) != (self.status in {'approved', 'consumed'}):
            raise ValueError('Only approved and consumed preparations have a grant')
        if (self.session_id is not None) != (self.status == 'consumed'):
            raise ValueError('Only a consumed preparation has its session')
        if (self.validity == 'closed') != (self.status in {'declined', 'consumed'}):
            raise ValueError('Closed validity must retain the terminal preparation fact')
        return self


class CodexBootstrapDecisionAck(BootstrapModel):
    preparation_id: dm.Id
    revision: RevisionTwo
    actor_session_id: dm.Id
    decision: Literal['approve_once', 'decline']
    operation_sha256: dm.Sha256
    consent_id: dm.Id | None
    decided_at: dm.UTC

    @model_validator(mode='after')
    def decision_grant(self) -> Self:
        if (self.consent_id is not None) != (self.decision == 'approve_once'):
            raise ValueError('Only approval creates a grant')
        return self


class CodexSessionCreateWrite(BootstrapModel):
    sandbox_root_id: dm.Id
    consent_id: dm.Id
    allowed_actions: EmptyActions


class CodexSessionCreateAck(BootstrapModel):
    id: dm.Id
    revision: RevisionTwo
    status: Literal['ready']
    capabilities: CodexBootstrapFeatures
    adapter_version: SafeLabel


class CodexSessionView(BootstrapModel):
    id: dm.Id
    revision: dm.Revision
    status: Literal['initializing', 'ready', 'failed', 'unknown']
    active_turn_id: None
    adapter_version: SafeLabel
    capabilities: CodexBootstrapFeatures

    @model_validator(mode='after')
    def state_revision(self) -> Self:
        if self.revision != (1 if self.status == 'initializing' else 2):
            raise ValueError('Session status and revision disagree')
        return self
