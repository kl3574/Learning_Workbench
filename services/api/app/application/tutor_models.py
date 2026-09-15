"""Immutable Tutor owner inputs, sole PRODUCT_DESIGN 3.0.4 appendix D."""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes

from ..provider_dto import NonEmpty
from ..tutor_dto import (
    TutorContextBinding, TutorContextOmission, TutorInputMaterial, TutorModel, TutorRunCreate,
)


class TutorFrozenHistoryItem(TutorModel):
    message_id: dm.Id
    source_run_id: dm.Id
    role: Literal['user', 'assistant']
    content_markdown: str
    content_sha256: dm.Sha256

    @model_validator(mode='after')
    def history_bytes(self) -> Self:
        if sha256_bytes(self.content_markdown.encode('utf-8')) != self.content_sha256:
            raise ValueError('history content must match its frozen UTF-8 hash')
        return self


class TutorJobInput(TutorModel):
    version: Literal['tutor-job-v1']
    workspace_id: dm.Id
    run_id: dm.Id
    request: TutorRunCreate
    history: Annotated[list[TutorFrozenHistoryItem], Field(max_length=4)]

    @model_validator(mode='after')
    def input_identity(self) -> Self:
        if self.workspace_id != self.request.request.workspace_id:
            raise ValueError('job input workspace must match its actual request')
        if len({item.message_id for item in self.history}) != len(self.history):
            raise ValueError('job history must not duplicate a message')
        if any(item.source_run_id == self.run_id for item in self.history):
            raise ValueError('a new run cannot include its own answer as prior history')
        return self


class PreparedTutorContext(TutorModel):
    version: Literal['tutor-context-v1']
    run_id: dm.Id
    snapshot: dm.ContextSnapshot
    binding: TutorContextBinding
    template_version: NonEmpty
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=6)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    included: list[TutorInputMaterial]
    history_message_ids: Annotated[list[dm.Id], Field(max_length=4)]
    omissions: list[TutorContextOmission]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def preparation_shape(self) -> Self:
        if self.messages[0].role != 'system' or self.messages[-1].role != 'user':
            raise ValueError('prepared messages require a system template and current user question')
        if any(item.role not in {'user', 'assistant'} for item in self.messages[1:-1]):
            raise ValueError('history cannot gain system instruction authority')
        if (len(self.history_message_ids) != len(self.messages) - 2
                or len(set(self.history_message_ids)) != len(self.history_message_ids)):
            raise ValueError('each actual history message needs a distinct frozen identity')
        if len(self.evidence) != len(self.included):
            raise ValueError('input summaries must correspond one-to-one with actual evidence')
        character_count = sum(len(message.content) for message in self.messages)
        for evidence, material in zip(self.evidence, self.included):
            reference = material.reference
            if (reference.ref != evidence.ref or reference.locator != evidence.locator
                    or reference.character_count != len(evidence.text)
                    or reference.excerpt_sha256 != sha256_bytes(evidence.text.encode('utf-8'))):
                raise ValueError('input material summary must match its complete actual text')
            envelope = '<reference>\n' + canonical_bytes({
                'ref': evidence.ref.model_dump(mode='json'), 'locator': evidence.locator,
                'text': evidence.text,
            }).decode('utf-8') + '\n</reference>'
            character_count += len(envelope)
        if self.snapshot.character_count != character_count or character_count > 12000:
            raise ValueError('context character count must include complete messages and reference envelopes')
        return self


def context_sha256(context: PreparedTutorContext) -> str:
    """The sole excluded field avoids a self-referential context hash."""
    value = context.model_dump(mode='json')
    del value['snapshot']['snapshot_sha256']
    return sha256_bytes(canonical_bytes(value))
