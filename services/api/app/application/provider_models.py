"""Closed private preparation/protocol models, sole spec v3.0.2 appendix D.

Actual cumulative usage, channel bytes, receipt hashes, artifact existence,
source ownership and authorization are verified by their owning ports. These
models cannot authorize a hand-built envelope or prove private artifact bytes.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from ..provider_dto import NonEmpty, NonNegativeInt, OutboundPurpose, ProviderFailureCode


class PreparedOutboundMaterial(dm.StrictModel):
    job_id: dm.Id
    job_revision: dm.Revision
    job_input_sha256: dm.Sha256
    purpose: OutboundPurpose
    context_snapshot: dm.ContextSnapshot
    messages: list[dm.GenerationMessage]
    evidence: list[dm.EvidenceChunk]
    preparation_version: NonEmpty
    prepared_input_sha256: dm.Sha256


class DispatchLease(dm.StrictModel):
    owner_id: dm.Id
    job_revision: dm.Revision
    expires_at: dm.UTC


class UsageSnapshot(dm.StrictModel):
    input_tokens: NonNegativeInt | None
    output_tokens: NonNegativeInt | None


class CheckedProviderDelta(dm.StrictModel):
    type: Literal['delta']
    channel: Literal['answer', 'refusal']
    # A transport chunk can consist solely of meaningful whitespace. Unlike
    # configuration strings it must preserve that text, including a final LF.
    text: Annotated[str, Field(min_length=1)]


class CheckedProviderUsage(dm.StrictModel):
    type: Literal['usage']
    input_tokens: NonNegativeInt | None
    output_tokens: NonNegativeInt | None

    @model_validator(mode='after')
    def has_known_usage(self) -> Self:
        if self.input_tokens is None and self.output_tokens is None:
            raise ValueError('a usage event must report at least one known count')
        return self


class CheckedProviderFinished(dm.StrictModel):
    type: Literal['finished']
    outcome: Literal['complete', 'refused', 'incomplete']
    reason: Literal['output_limit', 'content_filter', 'provider_incomplete'] | None
    output_state: Literal['none', 'partial', 'complete']
    usage: UsageSnapshot

    @model_validator(mode='after')
    def terminal_meaning(self) -> Self:
        if self.outcome == 'incomplete':
            if self.reason is None or self.output_state == 'complete':
                raise ValueError('incomplete requires a reason and cannot claim complete output')
        elif self.reason is not None or self.output_state == 'partial':
            raise ValueError('complete/refused requires no incomplete reason or partial output')
        return self


class CheckedProviderError(dm.StrictModel):
    type: Literal['error']
    error_code: ProviderFailureCode
    provider_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown']
    output_state: Literal['none', 'partial']
    usage: UsageSnapshot


CheckedProviderEvent = Annotated[
    CheckedProviderDelta | CheckedProviderUsage | CheckedProviderFinished | CheckedProviderError,
    Field(discriminator='type'),
]
CheckedProviderTerminal = Annotated[CheckedProviderFinished | CheckedProviderError, Field(discriminator='type')]


class ProviderTerminalReceipt(dm.StrictModel):
    id: dm.Id
    workspace_id: dm.Id
    dispatch_id: dm.Id
    job_id: dm.Id
    consent_id: dm.Id
    proposal_id: dm.Id
    request_body_sha256: dm.Sha256
    terminal: CheckedProviderTerminal
    answer_artifact_id: dm.Id | None
    refusal_artifact_id: dm.Id | None
    recorded_at: dm.UTC
    receipt_sha256: dm.Sha256

    @model_validator(mode='after')
    def output_artifacts(self) -> Self:
        has_artifact = self.answer_artifact_id is not None or self.refusal_artifact_id is not None
        if (self.terminal.output_state == 'none') == has_artifact:
            raise ValueError('output state must match the presence of channel artifacts')
        if isinstance(self.terminal, CheckedProviderFinished):
            if self.terminal.outcome == 'complete' and self.refusal_artifact_id is not None:
                raise ValueError('normal completion cannot include a refusal channel')
            if (self.terminal.outcome == 'refused' and self.terminal.output_state == 'complete'
                    and self.refusal_artifact_id is None):
                raise ValueError('complete refusal output requires a refusal artifact')
        return self
