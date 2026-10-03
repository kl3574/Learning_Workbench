"""Target contracts v3.0.0, not a running product. Python 3.12 / Pydantic 2.
Unknown fields are rejected. Cross-object permissions, references, DAGs and hashes
require semantic validation in application services; JSON shape alone is insufficient.
"""
from __future__ import annotations
from typing import Annotated, Literal
from pathlib import PurePosixPath
from datetime import datetime
from pydantic import AfterValidator
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Id = Annotated[str, StringConstraints(pattern=r'^[A-Za-z][A-Za-z0-9_-]{0,79}$')]
Sha256 = Annotated[str, StringConstraints(pattern=r'^[a-f0-9]{64}$')]
def valid_utc(value: str) -> str:
    datetime.fromisoformat(value[:-1] + '+00:00')
    return value
UTC = Annotated[str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'), AfterValidator(valid_utc)]
Revision = Annotated[int, Field(ge=1)]
Text = Annotated[str, StringConstraints(min_length=1, max_length=400000)]
Entity = Literal['course','lesson','block','concept','route','question','practice_set','assessment','note']
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
class ContentRef(StrictModel):
    entity: Entity
    id: Id
    revision: Revision
    sha256: Sha256
class Header(StrictModel):
    schema_version: Literal['3.0.0'] = '3.0.0'
    id: Id
    revision: Revision
class FileEntry(StrictModel):
    path: str
    size: int = Field(ge=0, le=209715200)
    sha256: Sha256
    media_type: str
    visibility: Literal['learner','author_private']
    @model_validator(mode='after')
    def safe_path(self):
        p=PurePosixPath(self.path)
        if not self.path or '\\' in self.path or p.is_absolute() or '..' in p.parts or str(p)!=self.path or ':' in self.path:
            raise ValueError('payload path must be canonical relative POSIX path')
        if self.path=='manifest.json': raise ValueError('manifest must not hash itself')
        return self
class Manifest(StrictModel):
    schema_version: Literal['3.0.0']='3.0.0'
    format: Literal['learning-package']='learning-package'
    package_id: Id
    profile: Literal['learner','author']
    created_at: UTC
    root_course: str = 'course.json'
    files: list[FileEntry] = Field(min_length=1, max_length=2000)
    @model_validator(mode='after')
    def unique_files(self):
        paths=[f.path for f in self.files]
        if len(set(paths))!=len(paths): raise ValueError('duplicate path')
        if self.root_course not in paths: raise ValueError('missing root_course')
        if self.profile=='learner' and any(f.visibility!='learner' or f.path.startswith('private/') for f in self.files):
            raise ValueError('learner package cannot contain private files')
        return self
class Concept(Header):
    entity: Literal['concept']='concept'
    title: Text
    prerequisite_ids: list[Id]=Field(default_factory=list)
    skill_dimensions: list[Literal['recall','explain','compute','derive','transfer']]=Field(default_factory=list)
class Symbol(StrictModel):
    id: Id
    tex: str
    meaning: str
    domain: str
    dimension: str
    scope: Id
    first_definition: ContentRef
class Citation(StrictModel):
    id: Id
    title: str
    url: str | None = None
    locator: str
    source_sha256: Sha256 | None = None
    verification: Literal['verified','unverified','user_supplied']
class ContentBlock(Header):
    entity: Literal['block']='block'
    kind: Literal['orientation','definition','theorem','proof','intuition','worked_example','boundary','summary','text','code','figure']
    title: Text
    body_path: str
    body_sha256: Sha256
    concepts: list[Id]=Field(default_factory=list)
    citations: list[Id]=Field(default_factory=list)
    depends_on: list[ContentRef]=Field(default_factory=list)
    @model_validator(mode='after')
    def body_path_safe(self):
        p=PurePosixPath(self.body_path)
        if p.is_absolute() or '..' in p.parts or str(p)!=self.body_path or '\\' in self.body_path or ':' in self.body_path:
            raise ValueError('body path must be canonical relative POSIX path')
        return self
class Lesson(Header):
    entity: Literal['lesson']='lesson'
    title: Text
    objectives: list[str]
    prerequisite_ids: list[Id]=Field(default_factory=list)
    block_refs: list[ContentRef]=Field(min_length=1)
    proof_policy: Literal['full','declared_dependencies']='full'
class CourseSection(StrictModel):
    id: Id
    title: Text
    lesson_ids: list[Id]=Field(min_length=1)
class Course(Header):
    entity: Literal['course']='course'
    title: Text
    language: str='zh-CN'
    audience: str
    lesson_refs: list[ContentRef]=Field(min_length=1)
    concept_refs: list[ContentRef]=Field(default_factory=list)
    sections: list[CourseSection]=Field(default_factory=list)
    objectives: list[str]=Field(default_factory=list)
    difficulty: Literal['beginner','intermediate','advanced']='beginner'
    @model_validator(mode='after')
    def sections_cover_lessons(self):
        ids=[r.id for r in self.lesson_refs]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate lesson ref')
        if self.sections:
            members=[i for section in self.sections for i in section.lesson_ids]
            if len(members)!=len(set(members)) or set(members)!=set(ids):
                raise ValueError('sections must partition lesson refs')
            section_ids=[x.id for x in self.sections]
            if len(section_ids)!=len(set(section_ids)): raise ValueError('duplicate section id')
        return self
class RouteStep(StrictModel):
    id: Id
    title: str
    target: ContentRef
    requires_steps: list[Id]=Field(default_factory=list)
    completion_rule: Literal['manual','read','practice_submitted','assessment_submitted']
class Route(Header):
    entity: Literal['route']='route'
    title: str
    goal: str
    steps: list[RouteStep]=Field(min_length=1)
class Choice(StrictModel):
    id: Id
    text_markdown: Text
class QuestionPublic(Header):
    entity: Literal['question']='question'
    kind: Literal['single_choice','text_blank','numeric','expression','calculation']
    stem_markdown: Text
    choices: list[Choice]=Field(default_factory=list)
    concept_ids: list[Id]=Field(min_length=1)
    skill: Literal['recall','explain','compute','derive','transfer']
    exposure_group: Id
    max_score: float=Field(gt=0,le=100,default=1)
    input_instructions: str
    @model_validator(mode='after')
    def choices_match(self):
        ids=[x.id for x in self.choices]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate choice ID')
        if self.kind=='single_choice' and len(ids)<2: raise ValueError('choice question needs options')
        if self.kind!='single_choice' and ids: raise ValueError('non-choice question cannot have options')
        return self
class SolutionPrivate(Header):
    question_ref: ContentRef
    grading_kind: Literal['choice_exact','text_normalized','numeric_tolerance','symbolic_review','rubric_review']
    accepted_answers: list[str]=Field(min_length=1)
    absolute_tolerance: float=Field(default=0,ge=0)
    relative_tolerance: float=Field(default=0,ge=0)
    unit: str | None=None
    domain_assumptions: list[str]=Field(default_factory=list)
    solution_markdown: Text
    rubric_markdown: str=''
    review_status: Literal['draft','needs_review','approved']
class PracticeSet(Header):
    entity: Literal['practice_set']='practice_set'
    title: str
    lesson_ref: ContentRef
    question_refs: list[ContentRef]=Field(min_length=1)
    feedback_policy: Literal['on_submit_or_reveal']='on_submit_or_reveal'
class AssessmentBlueprint(Header):
    entity: Literal['assessment']='assessment'
    title: str
    question_refs: list[ContentRef]=Field(min_length=1)
    allowed_modes: list[Literal['independent','assisted','open_book']]=Field(min_length=1)
    time_limit_seconds: int | None=Field(default=None,gt=0)
class PolicySnapshot(StrictModel):
    policy_version: Literal['1.0.0']='1.0.0'
    mode: Literal['independent','assisted','open_book']
    tutor_scope: Literal['operation_help_only','academic']
    allow_web: bool
    allow_materials: bool
    solution_release: Literal['after_submit']='after_submit'
    @model_validator(mode='after')
    def independent(self):
        if self.mode=='open_book' and (self.tutor_scope!='operation_help_only' or self.allow_web or not self.allow_materials):
            raise ValueError('open-book allows materials, not academic tools')
        if self.mode=='assisted' and (self.tutor_scope!='academic' or not self.allow_materials):
            raise ValueError('assisted must declare academic help and materials')
        if self.mode=='independent' and (self.tutor_scope!='operation_help_only' or self.allow_web or self.allow_materials):
            raise ValueError('independent policy cannot allow academic assistance')
        return self
class AttemptCreate(StrictModel):
    assessment_ref: ContentRef
    mode: Literal['independent','assisted','open_book']
class AttemptPublic(StrictModel):
    id: Id
    workspace_id: Id
    assessment_ref: ContentRef
    status: Literal['active','submitted','grading','graded','needs_review','abandoned']
    policy: PolicySnapshot
    questions: list[QuestionPublic]
    revision: Revision
    created_at: UTC
    deadline_at: UTC | None=None
    submitted_at: UTC | None=None
class ResponseDraft(StrictModel):
    question_id: Id
    answer: str=Field(max_length=4000)
    steps_markdown: str=Field(default='',max_length=20000)
class ResponsesWrite(StrictModel):
    expected_revision: Revision
    responses: list[ResponseDraft]
class AttemptSubmit(StrictModel):
    expected_revision: Revision
class ItemGrade(StrictModel):
    question_ref: ContentRef
    score: float | None=Field(default=None,ge=0)
    max_score: float=Field(gt=0)
    status: Literal['graded','needs_review']
    feedback_markdown: str
    solution_markdown: str | None=None
    @model_validator(mode='after')
    def valid_score(self):
        if self.status=='graded' and self.score is None: raise ValueError('resolved grade needs score')
        if self.status=='needs_review' and self.score is not None: raise ValueError('unresolved score must be null')
        if self.score is not None and self.score>self.max_score: raise ValueError('score exceeds max')
        return self
class GradingResult(StrictModel):
    attempt_id: Id
    grading_revision: Revision
    grading_rules_version: str
    status: Literal['graded','needs_review']
    items: list[ItemGrade]
    finalized_at: UTC
class Selection(StrictModel):
    ref: ContentRef
    exact_quote: str=Field(max_length=12000)
    prefix: str=''
    suffix: str=''
    start_codepoint: int=Field(ge=0)
    end_codepoint: int=Field(ge=0)
    @model_validator(mode='after')
    def range_ok(self):
        if self.end_codepoint<self.start_codepoint: raise ValueError('reversed range')
        return self
class Note(Header):
    entity: Literal['note']='note'
    workspace_id: Id
    anchor: Selection
    markdown: Text
    anchor_state: Literal['exact','stale','unresolved']='exact'
class ViewContext(StrictModel):
    view_kind: Literal['route','lesson','worked_example','practice','assessment_help','assessment_review','authoring']
    active_ref: ContentRef
    attached_refs: list[ContentRef]=Field(default_factory=list,max_length=8)
    selection: Selection | None=None
    attempt_id: Id | None=None
class TutorRequest(StrictModel):
    thread_id: Id
    workspace_id: Id
    message: str=Field(min_length=1,max_length=8000)
    intent: Literal['explain','hint','derive','research']
    context: ViewContext
    web_search: bool=False
    consent_id: Id | None=None
class ContextSnapshot(StrictModel):
    id: Id
    created_at: UTC
    request_sha256: Sha256
    resolved_refs: list[ContentRef]
    policy: Literal['learning','practice','test_help','review','authoring']
    character_count: int=Field(ge=0)
    snapshot_sha256: Sha256
class ProviderCapabilities(StrictModel):
    provider_id: Id
    configured: bool
    chat: bool
    structured_output: bool
    web_search: bool
    streaming: bool
    tool_calls: bool
    version_evidence: str
class RunSnapshot(StrictModel):
    id: Id
    thread_id: Id
    status: Literal['queued','running','awaiting_approval','completed','failed','cancelled']
    context_snapshot_id: Id | None=None
    last_seq: int=Field(ge=0)
    answer_markdown: str=''
    citations: list[Citation]=Field(default_factory=list)
    search_status: Literal['not_requested','not_executed','executed','failed']='not_requested'
class RunEvent(StrictModel):
    run_id: Id
    seq: int=Field(ge=1)
    type: Literal['queued','context_ready','retrieval_completed','answer_delta','citation','approval_required','usage','completed','failed','cancelled']
    occurred_at: UTC
    text: str | None=None
    context_snapshot_id: Id | None=None
    citation: Citation | None=None
    approval_id: Id | None=None
    input_tokens: int | None=Field(default=None,ge=0)
    output_tokens: int | None=Field(default=None,ge=0)
    error_code: str | None=None
    @model_validator(mode='after')
    def payload_matches(self):
        required={'answer_delta':'text','citation':'citation','context_ready':'context_snapshot_id','approval_required':'approval_id','failed':'error_code'}
        if self.type in required and getattr(self,required[self.type]) is None: raise ValueError('missing typed event payload')
        return self
class LearningEvent(StrictModel):
    event_id: Id
    workspace_id: Id
    actor: Literal['learner','server','import']
    origin: Literal['native','user_supplied_import']
    kind: Literal['read_marked','hint_revealed','solution_revealed','practice_submitted','test_submitted','grade_finalized','note_created']
    ref: ContentRef
    occurred_at: UTC
    attempt_id: Id | None=None
class Evidence(StrictModel):
    id: Id
    event_id: Id
    concept_id: Id
    skill: Literal['recall','explain','compute','derive','transfer']
    eligible: bool
    reason: str
    score: float | None=Field(default=None,ge=0,le=1)
    independence: Literal['independent','assisted','unknown']
    freshness: Literal['novel','repeated','unknown']
class Recommendation(StrictModel):
    id: Id
    target: ContentRef
    reason_code: Literal['prerequisite_gap','assessment_error','review_due','next_route_step','user_goal']
    explanation: str
    evidence_ids: list[Id]
    decision: Literal['pending','accepted','dismissed']='pending'
    action: Literal['read','practice','test','review','inspect_source']='read'
    prerequisite_gaps: list[Id]=Field(default_factory=list)
    estimated_minutes: int | None=Field(default=None,gt=0)
    rule_version: str='rules-1.0.0'
    generated_at: UTC
    staleness: Literal['current','stale']='current'
class AuthoringRequest(StrictModel):
    topic: Text
    prerequisites: list[str]
    objectives: list[str]
    proof_policy: Literal['full','declared_dependencies']
    output_kind: Literal['lesson','worked_example','practice_set','assessment']
    source_refs: list[ContentRef]
    provider_id: Id
    consent_id: Id
class DraftCandidate(StrictModel):
    draft_id: Id
    draft_revision: Revision
    entity: Entity
    candidate_sha256: Sha256
class ReviewReceipt(StrictModel):
    id: Id
    revision: Revision=1
    candidate: DraftCandidate
    structural: Literal['PASS','FAIL','NOT_RUN','BLOCKED']
    mathematical: Literal['APPROVED','REJECTED','NOT_RUN','NOT_APPLICABLE']
    sources: Literal['APPROVED','REJECTED','NOT_RUN','NOT_APPLICABLE']
    independent_pedagogy: Literal['PASS','FAIL','NOT_RUN','BLOCKED']
    reviewer: str
    created_at: UTC
    evidence_paths: list[str]
    decision_reason: str
class ApprovalDecision(StrictModel):
    operation_sha256: Sha256
    decision: Literal['approve_once','decline']
    expected_revision: Revision
class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: Id
    retryable: bool
    details: list[str]=Field(default_factory=list)
class ErrorEnvelope(StrictModel):
    error: ErrorDetail

class Warning(StrictModel):
    code: str
    message: str
    locator: str | None=None
    severity: Literal['info','warning','error']
class JobRef(StrictModel):
    id: Id
    status: Literal['queued','running','awaiting_approval','completed','failed','cancelled']
class MutationAck(StrictModel):
    id: Id
    revision: Revision
    applied: bool
class SelfAssessment(StrictModel):
    concept_id: Id
    level: Literal['not_learned','encountered','independent_use']
    origin: Literal['self_report']='self_report'
    updated_at: UTC
class LearnerProfile(StrictModel):
    workspace_id: Id
    revision: Revision
    goals: list[str]=Field(default_factory=list)
    goal_concept_ids: list[Id]=Field(default_factory=list)
    weekly_minutes: int=Field(default=120,ge=1,le=10080)
    language: str='zh-CN'
    preferred_difficulty: Literal['beginner','intermediate','advanced']='beginner'
    self_assessments: list[SelfAssessment]=Field(default_factory=list)
class SavedTab(StrictModel):
    id: Id
    context: ViewContext
    pinned: bool
    scroll_offset: float=Field(default=0,ge=0)
class WorkbenchSession(StrictModel):
    revision: Revision
    course_ref: ContentRef | None=None
    navigation: Literal['route','textbook','practice','assessment']='route'
    tabs: list[SavedTab]=Field(default_factory=list,max_length=100)
    active_tab_id: Id | None=None
    expanded_keys: list[str]=Field(default_factory=list,max_length=10000)
    directory_scroll: float=Field(default=0,ge=0)
    nav_width: int=Field(default=300,ge=260,le=360)
    agent_width: int=Field(default=368,ge=320,le=480)
    nav_collapsed: bool=False
    agent_collapsed: bool=False
class SearchSource(StrictModel):
    id: Id
    title: str
    url: str
    retrieved_at: UTC
    locator: str
    excerpt: str
    verification: Literal['verified','unverified']='unverified'
class EvidenceChunk(StrictModel):
    ref: ContentRef
    locator: str
    text: str=Field(max_length=12000)
class GenerationMessage(StrictModel):
    role: Literal['system','user','assistant']
    content: str
class GenerationInput(StrictModel):
    # Internal only; never returned by general browser/readback endpoints.
    snapshot_id: Id
    snapshot_sha256: Sha256
    messages: list[GenerationMessage]
    evidence: list[EvidenceChunk]
    max_input_tokens: int=Field(gt=0)
    max_output_tokens: int=Field(gt=0)
    consent_id: Id
    web_search: bool=False
class ProviderEvent(StrictModel):
    type: Literal['delta','citation','usage','search_executed','finished','error']
    text: str | None=None
    citation: Citation | None=None
    input_tokens: int | None=Field(default=None,ge=0)
    output_tokens: int | None=Field(default=None,ge=0)
    error_code: str | None=None

CONTRACTS={name: value for name,value in list(globals().items()) if isinstance(value,type) and issubclass(value,StrictModel) and value not in (StrictModel,Header)}
