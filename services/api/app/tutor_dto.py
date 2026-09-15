"""Closed Tutor HTTP contracts, sole PRODUCT_DESIGN 3.0.4 appendix A.

Shape and local relationships do not establish source ownership, Policy, real
history, citation support, or authorization. Owner ports verify those facts.
"""
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, TypeAdapter, model_validator
from pydantic.json_schema import SkipJsonSchema

from packages.contracts import domain_models as dm

from .application.provider_models import UsageSnapshot
from .provider_dto import FalseOnly, NonEmpty, NonNegativeInt, ProviderFailureCode, ReferenceSummary, _omit_schema_default


def _unicode(value: object) -> None:
    if isinstance(value, str):
        try:
            value.encode('utf-8', errors='strict')
        except UnicodeError:
            raise ValueError('valid Unicode scalar values are required') from None
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            _unicode(getattr(value, name))
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode(key)
            _unicode(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _unicode(item)


class TutorModel(dm.StrictModel):
    @model_validator(mode='before')
    @classmethod
    def unicode_values(cls, value: object) -> object:
        _unicode(value)
        return value


class TutorPracticeBinding(TutorModel):
    session_id: dm.Id
    session_revision: dm.Revision
    question_ref: dm.ContentRef

    @model_validator(mode='after')
    def question_entity(self) -> Self:
        if self.question_ref.entity != 'question':
            raise ValueError('practice binding requires an exact question reference')
        return self


class TutorAssessmentBinding(TutorModel):
    attempt_revision: dm.Revision
    question_ref: dm.ContentRef
    grading_revision: dm.Revision | None

    @model_validator(mode='after')
    def question_entity(self) -> Self:
        if self.question_ref.entity != 'question':
            raise ValueError('assessment binding requires an exact question reference')
        return self


class TutorContextBinding(TutorModel):
    practice: TutorPracticeBinding | None
    assessment: TutorAssessmentBinding | None

    @model_validator(mode='after')
    def exclusive_binding(self) -> Self:
        if self.practice is not None and self.assessment is not None:
            raise ValueError('practice and assessment bindings are mutually exclusive')
        return self


def validate_context_binding(context: dm.ViewContext, binding: TutorContextBinding) -> None:
    """Check shape only; actual parent/session/question membership is owner-owned."""
    kind = context.view_kind
    if kind == 'practice':
        valid = (context.active_ref.entity == 'practice_set' and context.attempt_id is None
                 and binding.practice is not None and binding.assessment is None)
    elif kind in {'assessment_help', 'assessment_review'}:
        assessment = binding.assessment
        valid = (context.active_ref.entity == 'assessment' and context.attempt_id is not None
                 and binding.practice is None and assessment is not None
                 and ((assessment.grading_revision is None) == (kind == 'assessment_help')))
    else:
        valid = (kind in {'route', 'lesson', 'worked_example'}
                 and context.active_ref.entity in {'route': {'route'}, 'lesson': {'lesson', 'block'},
                                                   'worked_example': {'block'}}.get(kind, set())
                 and context.attempt_id is None
                 and binding.practice is None and binding.assessment is None)
    if not valid:
        raise ValueError('context kind, exact root and required interaction binding disagree')


def _explicit_context(value: object) -> None:
    if isinstance(value, dict) and set(value) != {
        'view_kind', 'active_ref', 'attached_refs', 'selection', 'attempt_id',
    }:
        raise ValueError('all current context fields must be explicit')


class TutorViewContext(dm.ViewContext):
    attached_refs: Annotated[list[dm.ContentRef], Field(max_length=8)]
    selection: dm.Selection | None
    attempt_id: dm.Id | None

    @model_validator(mode='before')
    @classmethod
    def from_core(cls, value: object) -> object:
        return value.model_dump(mode='json') if isinstance(value, dm.ViewContext) else value


class TutorRequestInput(dm.TutorRequest):
    context: TutorViewContext
    web_search: FalseOnly
    consent_id: None

    @model_validator(mode='before')
    @classmethod
    def from_core(cls, value: object) -> object:
        return value.model_dump(mode='json') if isinstance(value, dm.TutorRequest) else value


class TutorThreadCreate(TutorModel):
    scope: TutorViewContext
    binding: TutorContextBinding
    title: Annotated[NonEmpty, Field(max_length=200)]

    @model_validator(mode='before')
    @classmethod
    def explicit_scope(cls, value: object) -> object:
        if isinstance(value, dict):
            _explicit_context(value.get('scope'))
        return value

    @model_validator(mode='after')
    def scope_binding(self) -> Self:
        validate_context_binding(self.scope, self.binding)
        return self


class TutorThreadView(TutorThreadCreate):
    id: dm.Id
    revision: dm.Revision
    created_at: dm.UTC


class TutorPageQuery(TutorModel):
    cursor: NonEmpty | SkipJsonSchema[None] = Field(
        default=None, exclude_if=lambda value: value is None, json_schema_extra=_omit_schema_default,
    )
    limit: Annotated[int, Field(ge=1, le=100)] = 20

    @model_validator(mode='before')
    @classmethod
    def not_null_cursor(cls, value: object) -> object:
        if isinstance(value, dict) and value.get('cursor', '') is None:
            raise ValueError('cursor may be omitted but cannot be null')
        return value


class TutorThreadPage(TutorModel):
    items: list[TutorThreadView]
    next_cursor: NonEmpty | None

    @model_validator(mode='after')
    def distinct_items(self) -> Self:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('thread page cannot duplicate an identity')
        return self


class TutorMessage(TutorModel):
    id: dm.Id
    seq: Annotated[int, Field(ge=1)]
    run_id: dm.Id
    role: Literal['user', 'assistant']
    channel: Literal['answer', 'refusal'] | None
    status: Literal['stored', 'completed', 'failed', 'cancelled']
    content_markdown: str
    context_snapshot_id: dm.Id | None
    citations: list[dm.Citation]
    created_at: dm.UTC

    @model_validator(mode='after')
    def role_channel_status(self) -> Self:
        if self.role == 'user':
            if self.channel is not None or self.status != 'stored' or self.citations:
                raise ValueError('user messages have stored status and no generated channel or citations')
        elif self.channel is None or self.status == 'stored':
            raise ValueError('assistant messages require a channel and actual terminal status')
        return self


class TutorMessagePage(TutorModel):
    thread: TutorThreadView
    items: list[TutorMessage]
    next_cursor: NonEmpty | None

    @model_validator(mode='after')
    def ordered_messages(self) -> Self:
        seqs = [item.seq for item in self.items]
        if (len({item.id for item in self.items}) != len(self.items)
                or any(right != left + 1 for left, right in zip(seqs, seqs[1:]))):
            raise ValueError('message page identities and sequence must be distinct and contiguous')
        return self


class TutorRunCreate(TutorModel):
    request: TutorRequestInput
    expected_thread_revision: dm.Revision
    binding: TutorContextBinding

    @model_validator(mode='before')
    @classmethod
    def explicit_request(cls, value: object) -> object:
        if isinstance(value, dict):
            request = value.get('request')
            if isinstance(request, dict):
                if set(request) != {
                    'thread_id', 'workspace_id', 'message', 'intent', 'context', 'web_search', 'consent_id',
                }:
                    raise ValueError('all Tutor request fields must be explicit')
                _explicit_context(request.get('context'))
        return value

    @model_validator(mode='after')
    def local_unapproved_creation(self) -> Self:
        if self.request.web_search or self.request.consent_id is not None:
            raise ValueError('new runs prepare locally without search or an existing consent')
        if not self.request.message.strip():
            raise ValueError('a nonblank current question is required')
        validate_context_binding(self.request.context, self.binding)
        return self


class TutorInputMaterial(TutorModel):
    reference: ReferenceSummary
    body_sha256: dm.Sha256 | None
    material_review: Literal['unreviewed', 'not_applicable']

    @model_validator(mode='after')
    def material_kind(self) -> Self:
        if self.reference.ref.entity == 'block':
            valid = (self.material_review == 'unreviewed'
                     and self.body_sha256 == self.reference.excerpt_sha256)
        else:
            valid = self.body_sha256 is None and self.material_review == 'not_applicable'
        if not valid:
            raise ValueError('block bodies and other owner units have distinct review and hash meanings')
        return self


class TutorContextOmission(TutorModel):
    ref: dm.ContentRef | None
    reason: Literal[
        'character_budget', 'block_budget', 'history_budget', 'adapter_shape', 'index_missing',
        'index_stale', 'index_building', 'no_match', 'not_released', 'unavailable',
    ]
    message: NonEmpty


class TutorContextSummary(TutorModel):
    snapshot: dm.ContextSnapshot
    included: list[TutorInputMaterial]
    history_message_ids: Annotated[list[dm.Id], Field(max_length=4)]
    omissions: list[TutorContextOmission]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def distinct_history(self) -> Self:
        if len(set(self.history_message_ids)) != len(self.history_message_ids):
            raise ValueError('included history identities must be distinct')
        if len(self.included) > 8 or self.snapshot.character_count > 12000:
            raise ValueError('context summary exceeds the actual preparation budget')
        return self


TutorFailureCode = ProviderFailureCode | Literal[
    'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'TUTOR_CONTEXT_INVALID', 'TUTOR_CONTEXT_CHANGED',
    'TUTOR_CONTEXT_UNAVAILABLE', 'TUTOR_CONTEXT_BUDGET_EXCEEDED', 'TUTOR_OUTPUT_INVALID',
    'TUTOR_OUTPUT_EMPTY', 'TUTOR_INTEGRITY_ERROR', 'TUTOR_OUTCOME_UNKNOWN',
]


class TutorProviderResult(TutorModel):
    receipt_id: dm.Id
    receipt_sha256: dm.Sha256
    outcome: Literal['complete', 'refused', 'incomplete', 'error']
    provider_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown']
    output_state: Literal['none', 'partial', 'complete']

    @model_validator(mode='after')
    def provider_facts(self) -> Self:
        if self.outcome in {'complete', 'refused'}:
            valid = self.provider_outcome == 'completed' and self.output_state != 'partial'
        elif self.outcome == 'incomplete':
            valid = self.provider_outcome == 'incomplete' and self.output_state != 'complete'
        else:
            valid = self.output_state != 'complete'
        if not valid:
            raise ValueError('provider outcome and output state disagree')
        return self


class TutorResultSummary(TutorModel):
    refusal_markdown: str
    usage: UsageSnapshot
    provider: TutorProviderResult | None
    error_code: TutorFailureCode | None


class TutorRunView(TutorModel):
    run: dm.RunSnapshot
    job_revision: dm.Revision
    thread_revision: dm.Revision
    context: TutorContextSummary | None
    latest_proposal_id: dm.Id | None
    consent_id: dm.Id | None
    result: TutorResultSummary

    @model_validator(mode='after')
    def result_state(self) -> Self:
        context_id = self.context.snapshot.id if self.context else None
        if self.run.context_snapshot_id != context_id:
            raise ValueError('run and frozen context identities must match')
        if self.latest_proposal_id is not None and self.context is None:
            raise ValueError('a proposal requires a real frozen context')
        if self.consent_id is not None and self.latest_proposal_id is None:
            raise ValueError('a consent requires its actual proposal identity')
        if self.run.search_status != 'not_requested':
            raise ValueError('this Tutor stage cannot claim external search')
        if self.run.status == 'completed':
            provider = self.result.provider
            if (provider is None or provider.outcome != 'complete' or provider.output_state != 'complete'
                    or not self.run.answer_markdown or self.result.refusal_markdown
                    or self.result.error_code is not None or self.context is None):
                raise ValueError('completed requires actual complete non-refusal output and frozen context')
        elif self.run.status == 'failed':
            if self.result.error_code is None:
                raise ValueError('a failed run requires a bounded error code')
        elif self.run.status != 'cancelled' and self.result.error_code is not None:
            raise ValueError('nonterminal runs cannot claim a terminal error')
        return self


class TutorRunCancel(TutorModel):
    expected_revision: dm.Revision


class TutorRunControlView(TutorModel):
    id: dm.Id
    status: Literal['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled']
    job_revision: dm.Revision
    cancel_requested: bool


class TutorEventsQuery(TutorModel):
    after_seq: NonNegativeInt = 0


class TutorEventBase(TutorModel):
    run_id: dm.Id
    seq: Annotated[int, Field(ge=1)]
    occurred_at: dm.UTC


class TutorQueuedEvent(TutorEventBase):
    type: Literal['queued']


class TutorContextReadyEvent(TutorEventBase):
    type: Literal['context_ready']
    context_snapshot_id: dm.Id


class TutorRetrievalCompletedEvent(TutorEventBase):
    type: Literal['retrieval_completed']


class TutorAnswerDeltaEvent(TutorEventBase):
    type: Literal['answer_delta']
    text: Annotated[str, Field(min_length=1)]


class TutorCitationEvent(TutorEventBase):
    type: Literal['citation']
    citation: dm.Citation


class TutorApprovalRequiredEvent(TutorEventBase):
    type: Literal['approval_required']
    approval_id: dm.Id


class TutorUsageEvent(TutorEventBase):
    type: Literal['usage']
    input_tokens: NonNegativeInt | None
    output_tokens: NonNegativeInt | None

    @model_validator(mode='after')
    def known_count(self) -> Self:
        if self.input_tokens is None and self.output_tokens is None:
            raise ValueError('a usage event needs at least one real count')
        return self


class TutorCompletedEvent(TutorEventBase):
    type: Literal['completed']


class TutorFailedEvent(TutorEventBase):
    type: Literal['failed']
    error_code: TutorFailureCode


class TutorCancelledEvent(TutorEventBase):
    type: Literal['cancelled']


TutorSSEEvent = Annotated[
    TutorQueuedEvent | TutorContextReadyEvent | TutorRetrievalCompletedEvent | TutorAnswerDeltaEvent
    | TutorCitationEvent | TutorApprovalRequiredEvent | TutorUsageEvent | TutorCompletedEvent
    | TutorFailedEvent | TutorCancelledEvent,
    Field(discriminator='type'),
]
TUTOR_EVENT_ADAPTER: TypeAdapter[TutorSSEEvent] = TypeAdapter(TutorSSEEvent)
