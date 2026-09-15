// Generated from PRODUCT_DESIGN.md v3.0.6 and actual runtime OpenAPI; do not edit.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
import type { ApprovalDecision, AssessmentAttemptCreate, AssessmentGradingJob, AssessmentGradingResult, AttemptResponses, AttemptSnapshot, AttemptSubmit, AuthoringDraftView, AuthoringJobPage, AuthoringJobView, AuthoringPrepareWrite, BlockReadResponse, BootstrapRequest, BootstrapResponse, ConceptStateResponse, ConsentCreate, ConsentCreateAck, ConsentPage, ConsentPreviewWrite, ConsentProposalView, ConsentRevoke, ContentRef, Course, DirectorySearchResponse, EmptyRequest, HealthResponse, ImportCancelRequest, ImportCancelResponse, ImportCommitRequest, ImportCommitResponse, ImportDraftSnapshot, ImportPreview, ImportStaged, ImportUpload, JobCancelRequest, JobRef, JobSnapshot, LearnerProfile, LearningActionRequest, LearningActionResponse, LearningProgress, Lesson, LogoutResponse, MutationAck, Note, NoteDeleted, NumericCheckDecisionAck, NumericCheckPreviewWrite, NumericCheckView, OutlineResponse, PageAssessment, PageCourse, PageEvidence, PageNote, PagePracticeSet, PageRevision, PageRoute, PracticeHint, PracticeHintRequest, PracticeResponsesSaved, PracticeSession, PracticeSessionCreate, PracticeSessionCreated, PracticeSolution, PracticeSolutionRequest, PracticeSubmitRequest, PracticeSubmitted, PreferencesRequest, ProfileWrite, ProviderCapabilitiesResponse, ProviderConfigAck, ProviderConfigView, ProviderConfigWrite, ProviderSecretAck, ProviderSecretWrite, ReadinessResponse, RecommendationDecisionWrite, RecommendationPage, RegradeRequest, ResponsesWrite, RetrievalIndexOverview, RetrievalIndexRebuildWrite, RetrievalIndexScopeStatus, RetrievalQueryView, RetrievalQueryWrite, RoleRequest, Route, RouteCompletionRequest, SessionResponse, SourceResponse, TutorAnswerDeltaEvent, TutorApprovalRequiredEvent, TutorCancelledEvent, TutorCitationEvent, TutorCompletedEvent, TutorContextReadyEvent, TutorFailedEvent, TutorMessagePage, TutorQueuedEvent, TutorRetrievalCompletedEvent, TutorRunCancel, TutorRunControlView, TutorRunCreate, TutorRunView, TutorThreadCreate, TutorThreadPage, TutorThreadView, TutorUsageEvent, WorkbenchSaveRequest, WorkbenchSession, WorkspaceResponse } from "./api-types";

import type { RetrievalIndexStatusQuery } from "./retrieval-ports-binding";
export interface ApiEndpointMap {
  "GET /api/v1/artifacts/{id}/download": { request: undefined; response: Blob; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/assessments": { request: undefined; response: PageAssessment; headers: null; parameters: { query?: { "course_id"?: (string | null); "cursor"?: (string | null); "limit"?: number } }; parametersRequired: false };
  "POST /api/v1/assessments/{id}/attempts": { request: AssessmentAttemptCreate; response: AttemptSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/attempts/{id}": { request: undefined; response: AttemptSnapshot; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/attempts/{id}/abandon": { request: AttemptSubmit; response: AttemptSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/attempts/{id}/regrade": { request: RegradeRequest; response: JobRef; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/attempts/{id}/responses": { request: undefined; response: AttemptResponses; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "PUT /api/v1/attempts/{id}/responses": { request: ResponsesWrite; response: AttemptSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/attempts/{id}/result": { request: undefined; response: AssessmentGradingResult | AssessmentGradingJob; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/attempts/{id}/submit": { request: AttemptSubmit; response: AttemptSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/authoring/drafts/{id}": { request: undefined; response: AuthoringDraftView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/authoring/drafts/{id}/numeric-checks": { request: NumericCheckPreviewWrite; response: NumericCheckView; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/authoring/jobs": { request: undefined; response: AuthoringJobPage; headers: null; parameters: { query?: { "cursor"?: string; "limit"?: number } }; parametersRequired: false };
  "POST /api/v1/authoring/jobs": { request: AuthoringPrepareWrite; response: JobRef; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/authoring/jobs/{id}": { request: undefined; response: AuthoringJobView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/authoring/numeric-checks/{id}": { request: undefined; response: NumericCheckView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/authoring/numeric-checks/{id}/decision": { request: ApprovalDecision; response: NumericCheckDecisionAck; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/blocks/{id}": { request: undefined; response: BlockReadResponse; headers: null; parameters: { path: { "id": string }; query: { "include_provenance"?: boolean; "revision": number } }; parametersRequired: true };
  "GET /api/v1/blocks/{id}/body": { request: undefined; response: string; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/consents": { request: undefined; response: ConsentPage; headers: null; parameters: { query?: { "consent_id"?: (string | null); "cursor"?: (string | null); "limit"?: number } }; parametersRequired: false };
  "POST /api/v1/consents": { request: ConsentCreate; response: ConsentCreateAck; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/consents/preview": { request: ConsentPreviewWrite; response: ConsentProposalView; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/consents/preview/{id}": { request: undefined; response: ConsentProposalView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/consents/{id}/revoke": { request: ConsentRevoke; response: MutationAck; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/courses": { request: undefined; response: PageCourse; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number; "q"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/courses/{id}": { request: undefined; response: Course; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses/{id}/directory-search": { request: undefined; response: DirectorySearchResponse; headers: null; parameters: { path: { "id": string }; query: { "limit"?: number; "q": string; "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses/{id}/outline": { request: undefined; response: OutlineResponse; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/drafts/{id}": { request: undefined; response: ImportDraftSnapshot; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports": { request: ImportUpload; response: ImportStaged; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/imports/{id}": { request: undefined; response: ImportPreview; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports/{id}/cancel": { request: ImportCancelRequest; response: ImportCancelResponse; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports/{id}/commit": { request: ImportCommitRequest; response: ImportCommitResponse; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/index/rebuild": { request: RetrievalIndexRebuildWrite; response: JobRef; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/index/status": { request: undefined; response: (RetrievalIndexScopeStatus | RetrievalIndexOverview); headers: null; parameters: { query?: RetrievalIndexStatusQuery }; parametersRequired: false };
  "GET /api/v1/jobs/{id}": { request: undefined; response: JobSnapshot; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/jobs/{id}/cancel": { request: JobCancelRequest; response: JobSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/learner/profile": { request: undefined; response: LearnerProfile; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/learner/profile": { request: ProfileWrite; response: LearnerProfile; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/learning/actions": { request: LearningActionRequest; response: LearningActionResponse; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/learning/concept-states": { request: undefined; response: ConceptStateResponse; headers: null; parameters: { query?: { "course_id"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/learning/evidence": { request: undefined; response: PageEvidence; headers: null; parameters: { query?: { "concept_id"?: (string | null); "cursor"?: (string | null); "limit"?: number; "skill"?: ("recall" | "explain" | "compute" | "derive" | "transfer" | null) } }; parametersRequired: false };
  "GET /api/v1/learning/progress": { request: undefined; response: LearningProgress; headers: null; parameters: { query?: { "course_id"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/lessons/{id}": { request: undefined; response: Lesson; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/notes": { request: undefined; response: PageNote; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number; "ref_id"?: (string | null) } }; parametersRequired: false };
  "POST /api/v1/notes": { request: Note; response: ContentRef; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "DELETE /api/v1/notes/{id}": { request: undefined; response: NoteDeleted; headers: { "Idempotency-Key": string; "If-Match"?: (string | null) }; parameters: { path: { "id": string } }; parametersRequired: true };
  "PATCH /api/v1/notes/{id}": { request: Note; response: ContentRef; headers: { "Idempotency-Key": string; "If-Match"?: (string | null) }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/current": { request: undefined; response: ContentRef; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/revisions": { request: undefined; response: PageRevision; headers: null; parameters: { path: { "id": string }; query?: { "cursor"?: (string | null); "limit"?: number } }; parametersRequired: true };
  "POST /api/v1/practice/sessions": { request: PracticeSessionCreate; response: PracticeSessionCreated; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/practice/sessions/{id}": { request: undefined; response: PracticeSession; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/practice/sessions/{id}/hints": { request: PracticeHintRequest; response: PracticeHint; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "PUT /api/v1/practice/sessions/{id}/responses": { request: ResponsesWrite; response: PracticeResponsesSaved; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/practice/sessions/{id}/solutions": { request: PracticeSolutionRequest; response: PracticeSolution; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/practice/sessions/{id}/submit": { request: PracticeSubmitRequest; response: PracticeSubmitted; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/practice/sets": { request: undefined; response: PagePracticeSet; headers: null; parameters: { query?: { "course_id"?: (string | null); "cursor"?: (string | null); "lesson_id"?: (string | null); "limit"?: number } }; parametersRequired: false };
  "GET /api/v1/providers/capabilities": { request: undefined; response: ProviderCapabilitiesResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/providers/{id}/config": { request: undefined; response: ProviderConfigView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "PUT /api/v1/providers/{id}/config": { request: ProviderConfigWrite; response: ProviderConfigAck; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "DELETE /api/v1/providers/{id}/secret": { request: undefined; response: ProviderSecretAck; headers: { "Idempotency-Key": string; "If-Match": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/providers/{id}/secret": { request: ProviderSecretWrite; response: ProviderSecretAck; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/readiness": { request: undefined; response: ReadinessResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/recommendations": { request: undefined; response: RecommendationPage; headers: null; parameters: { query?: { "course_id"?: (string | null); "cursor"?: (string | null); "limit"?: number; "recommendation_id"?: (string | null) } }; parametersRequired: false };
  "POST /api/v1/recommendations/{id}/decision": { request: RecommendationDecisionWrite; response: MutationAck; headers: { "Idempotency-Key": string; "If-Match": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/retrieval/query": { request: RetrievalQueryWrite; response: RetrievalQueryView; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/routes": { request: undefined; response: PageRoute; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number } }; parametersRequired: false };
  "POST /api/v1/routes": { request: Route; response: ContentRef; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/routes/{id}": { request: Route; response: ContentRef; headers: { "Idempotency-Key": string; "If-Match"?: (string | null) }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/routes/{id}/steps/{step_id}/complete": { request: RouteCompletionRequest; response: LearningActionResponse; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string; "step_id": string } }; parametersRequired: true };
  "GET /api/v1/runs/{id}": { request: undefined; response: TutorRunView; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/runs/{id}/cancel": { request: TutorRunCancel; response: TutorRunControlView; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/runs/{id}/events": { request: undefined; response: AsyncIterable<TutorQueuedEvent | TutorContextReadyEvent | TutorRetrievalCompletedEvent | TutorAnswerDeltaEvent | TutorCitationEvent | TutorApprovalRequiredEvent | TutorUsageEvent | TutorCompletedEvent | TutorFailedEvent | TutorCancelledEvent>; headers: { "Last-Event-ID"?: string }; parameters: { path: { "id": string }; query?: { "after_seq"?: number } }; parametersRequired: true };
  "GET /api/v1/session": { request: undefined; response: SessionResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/bootstrap": { request: BootstrapRequest; response: BootstrapResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/logout": { request: EmptyRequest; response: LogoutResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/role": { request: RoleRequest; response: SessionResponse; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/sources/{id}": { request: undefined; response: SourceResponse; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/threads": { request: undefined; response: TutorThreadPage; headers: null; parameters: { query?: { "cursor"?: string; "limit"?: number } }; parametersRequired: false };
  "POST /api/v1/threads": { request: TutorThreadCreate; response: TutorThreadView; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/threads/{id}/messages": { request: undefined; response: TutorMessagePage; headers: null; parameters: { path: { "id": string }; query?: { "cursor"?: string; "limit"?: number } }; parametersRequired: true };
  "POST /api/v1/tutor/runs": { request: TutorRunCreate; response: TutorRunView; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/workbench/session": { request: undefined; response: WorkbenchSession; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workbench/session": { request: WorkbenchSaveRequest; response: WorkbenchSession; headers: { "If-Match"?: (string | null) }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/workspace": { request: undefined; response: WorkspaceResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workspace/preferences": { request: PreferencesRequest; response: MutationAck; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /health": { request: undefined; response: HealthResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
}

export const API_ENDPOINTS = {
  "GET /api/v1/artifacts/{id}/download": {
    "method": "GET",
    "path": "/api/v1/artifacts/{id}/download",
    "responseKind": "blob",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/assessments": {
    "method": "GET",
    "path": "/api/v1/assessments",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/assessments/{id}/attempts": {
    "method": "POST",
    "path": "/api/v1/assessments/{id}/attempts",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/attempts/{id}": {
    "method": "GET",
    "path": "/api/v1/attempts/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/attempts/{id}/abandon": {
    "method": "POST",
    "path": "/api/v1/attempts/{id}/abandon",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/attempts/{id}/regrade": {
    "method": "POST",
    "path": "/api/v1/attempts/{id}/regrade",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/attempts/{id}/responses": {
    "method": "GET",
    "path": "/api/v1/attempts/{id}/responses",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "PUT /api/v1/attempts/{id}/responses": {
    "method": "PUT",
    "path": "/api/v1/attempts/{id}/responses",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/attempts/{id}/result": {
    "method": "GET",
    "path": "/api/v1/attempts/{id}/result",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/attempts/{id}/submit": {
    "method": "POST",
    "path": "/api/v1/attempts/{id}/submit",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/authoring/drafts/{id}": {
    "method": "GET",
    "path": "/api/v1/authoring/drafts/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/authoring/drafts/{id}/numeric-checks": {
    "method": "POST",
    "path": "/api/v1/authoring/drafts/{id}/numeric-checks",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/authoring/jobs": {
    "method": "GET",
    "path": "/api/v1/authoring/jobs",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/authoring/jobs": {
    "method": "POST",
    "path": "/api/v1/authoring/jobs",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/authoring/jobs/{id}": {
    "method": "GET",
    "path": "/api/v1/authoring/jobs/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/authoring/numeric-checks/{id}": {
    "method": "GET",
    "path": "/api/v1/authoring/numeric-checks/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/authoring/numeric-checks/{id}/decision": {
    "method": "POST",
    "path": "/api/v1/authoring/numeric-checks/{id}/decision",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/blocks/{id}": {
    "method": "GET",
    "path": "/api/v1/blocks/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "include_provenance",
        "required": false,
        "type": "boolean"
      },
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/blocks/{id}/body": {
    "method": "GET",
    "path": "/api/v1/blocks/{id}/body",
    "responseKind": "text",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/consents": {
    "method": "GET",
    "path": "/api/v1/consents",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "consent_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/consents": {
    "method": "POST",
    "path": "/api/v1/consents",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/consents/preview": {
    "method": "POST",
    "path": "/api/v1/consents/preview",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/consents/preview/{id}": {
    "method": "GET",
    "path": "/api/v1/consents/preview/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/consents/{id}/revoke": {
    "method": "POST",
    "path": "/api/v1/consents/{id}/revoke",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/courses": {
    "method": "GET",
    "path": "/api/v1/courses",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "q",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/courses/{id}": {
    "method": "GET",
    "path": "/api/v1/courses/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/courses/{id}/directory-search": {
    "method": "GET",
    "path": "/api/v1/courses/{id}/directory-search",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 50
      },
      {
        "name": "q",
        "required": true,
        "type": "string"
      },
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/courses/{id}/outline": {
    "method": "GET",
    "path": "/api/v1/courses/{id}/outline",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/drafts/{id}": {
    "method": "GET",
    "path": "/api/v1/drafts/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports": {
    "method": "POST",
    "path": "/api/v1/imports",
    "responseKind": "json",
    "requestKind": "multipart",
    "multipartFields": [
      {
        "name": "file",
        "required": true,
        "binary": true
      },
      {
        "name": "kind",
        "required": true,
        "binary": false
      },
      {
        "name": "target_course_id",
        "required": false,
        "binary": false
      }
    ],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/imports/{id}": {
    "method": "GET",
    "path": "/api/v1/imports/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports/{id}/cancel": {
    "method": "POST",
    "path": "/api/v1/imports/{id}/cancel",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports/{id}/commit": {
    "method": "POST",
    "path": "/api/v1/imports/{id}/commit",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/index/rebuild": {
    "method": "POST",
    "path": "/api/v1/index/rebuild",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/index/status": {
    "method": "GET",
    "path": "/api/v1/index/status",
    "responseKind": "json",
    "queryMode": "retrieval-status",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "scope_refs",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/jobs/{id}": {
    "method": "GET",
    "path": "/api/v1/jobs/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/jobs/{id}/cancel": {
    "method": "POST",
    "path": "/api/v1/jobs/{id}/cancel",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/learner/profile": {
    "method": "GET",
    "path": "/api/v1/learner/profile",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/learner/profile": {
    "method": "PUT",
    "path": "/api/v1/learner/profile",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/learning/actions": {
    "method": "POST",
    "path": "/api/v1/learning/actions",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/learning/concept-states": {
    "method": "GET",
    "path": "/api/v1/learning/concept-states",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/learning/evidence": {
    "method": "GET",
    "path": "/api/v1/learning/evidence",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "concept_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "skill",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/learning/progress": {
    "method": "GET",
    "path": "/api/v1/learning/progress",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/lessons/{id}": {
    "method": "GET",
    "path": "/api/v1/lessons/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/notes": {
    "method": "GET",
    "path": "/api/v1/notes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "ref_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "POST /api/v1/notes": {
    "method": "POST",
    "path": "/api/v1/notes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "DELETE /api/v1/notes/{id}": {
    "method": "DELETE",
    "path": "/api/v1/notes/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "PATCH /api/v1/notes/{id}": {
    "method": "PATCH",
    "path": "/api/v1/notes/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/objects/{id}/current": {
    "method": "GET",
    "path": "/api/v1/objects/{id}/current",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/objects/{id}/revisions": {
    "method": "GET",
    "path": "/api/v1/objects/{id}/revisions",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/practice/sessions": {
    "method": "POST",
    "path": "/api/v1/practice/sessions",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/practice/sessions/{id}": {
    "method": "GET",
    "path": "/api/v1/practice/sessions/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/practice/sessions/{id}/hints": {
    "method": "POST",
    "path": "/api/v1/practice/sessions/{id}/hints",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "PUT /api/v1/practice/sessions/{id}/responses": {
    "method": "PUT",
    "path": "/api/v1/practice/sessions/{id}/responses",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/practice/sessions/{id}/solutions": {
    "method": "POST",
    "path": "/api/v1/practice/sessions/{id}/solutions",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/practice/sessions/{id}/submit": {
    "method": "POST",
    "path": "/api/v1/practice/sessions/{id}/submit",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/practice/sets": {
    "method": "GET",
    "path": "/api/v1/practice/sets",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "lesson_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "GET /api/v1/providers/capabilities": {
    "method": "GET",
    "path": "/api/v1/providers/capabilities",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/providers/{id}/config": {
    "method": "GET",
    "path": "/api/v1/providers/{id}/config",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "PUT /api/v1/providers/{id}/config": {
    "method": "PUT",
    "path": "/api/v1/providers/{id}/config",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "DELETE /api/v1/providers/{id}/secret": {
    "method": "DELETE",
    "path": "/api/v1/providers/{id}/secret",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/providers/{id}/secret": {
    "method": "POST",
    "path": "/api/v1/providers/{id}/secret",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/readiness": {
    "method": "GET",
    "path": "/api/v1/readiness",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/recommendations": {
    "method": "GET",
    "path": "/api/v1/recommendations",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      },
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "recommendation_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "POST /api/v1/recommendations/{id}/decision": {
    "method": "POST",
    "path": "/api/v1/recommendations/{id}/decision",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/retrieval/query": {
    "method": "POST",
    "path": "/api/v1/retrieval/query",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/routes": {
    "method": "GET",
    "path": "/api/v1/routes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/routes": {
    "method": "POST",
    "path": "/api/v1/routes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/routes/{id}": {
    "method": "PUT",
    "path": "/api/v1/routes/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/routes/{id}/steps/{step_id}/complete": {
    "method": "POST",
    "path": "/api/v1/routes/{id}/steps/{step_id}/complete",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      },
      {
        "name": "step_id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/runs/{id}": {
    "method": "GET",
    "path": "/api/v1/runs/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/runs/{id}/cancel": {
    "method": "POST",
    "path": "/api/v1/runs/{id}/cancel",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/runs/{id}/events": {
    "method": "GET",
    "path": "/api/v1/runs/{id}/events",
    "responseKind": "sse",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "after_seq",
        "required": false,
        "type": "integer",
        "minimum": 0
      }
    ]
  },
  "GET /api/v1/session": {
    "method": "GET",
    "path": "/api/v1/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/bootstrap": {
    "method": "POST",
    "path": "/api/v1/session/bootstrap",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/logout": {
    "method": "POST",
    "path": "/api/v1/session/logout",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/role": {
    "method": "POST",
    "path": "/api/v1/session/role",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/sources/{id}": {
    "method": "GET",
    "path": "/api/v1/sources/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/threads": {
    "method": "GET",
    "path": "/api/v1/threads",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/threads": {
    "method": "POST",
    "path": "/api/v1/threads",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/threads/{id}/messages": {
    "method": "GET",
    "path": "/api/v1/threads/{id}/messages",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "POST /api/v1/tutor/runs": {
    "method": "POST",
    "path": "/api/v1/tutor/runs",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/workbench/session": {
    "method": "GET",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workbench/session": {
    "method": "PUT",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/workspace": {
    "method": "GET",
    "path": "/api/v1/workspace",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workspace/preferences": {
    "method": "PUT",
    "path": "/api/v1/workspace/preferences",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /health": {
    "method": "GET",
    "path": "/health",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  }
} as const;

export type EndpointKey = keyof ApiEndpointMap;
export type ApiRequest<K extends EndpointKey> = ApiEndpointMap[K]['request'];
export type ApiResponse<K extends EndpointKey> = ApiEndpointMap[K]['response'];
export type ApiParameters<K extends EndpointKey> = ApiEndpointMap[K]['parameters'];
export type ApiHeaders<K extends EndpointKey> = ApiEndpointMap[K]['headers'] extends null
  ? undefined : ApiEndpointMap[K]['headers'];
export type ApiArgs<K extends EndpointKey> = ApiEndpointMap[K]['parametersRequired'] extends true
  ? [body: ApiRequest<K>, headers: ApiHeaders<K>, parameters: ApiParameters<K>]
  : ApiEndpointMap[K]['headers'] extends null
    ? [body: ApiRequest<K>, headers?: undefined, parameters?: ApiParameters<K>]
    : [body: ApiRequest<K>, headers: ApiHeaders<K>, parameters?: ApiParameters<K>];

export type ResponseKind = 'json' | 'text' | 'blob' | 'sse';
// The caller owns same-origin session/CSRF and HTTP error handling.
// Raw transport data is unknown; endpoint results always use generated DTOs.
export type ApiTransport = (path: string, init: RequestInit, responseKind?: ResponseKind) => Promise<unknown>;
export type JsonTransport = ApiTransport;
type Scalar = string | number | boolean | null | undefined;
type UrlParameters = { path?: Record<string, Scalar>; query?: Record<string, Scalar> };
type Parameter = {
  name: string; required: boolean; type: 'string' | 'integer' | 'number' | 'boolean';
  minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number;
};
type Endpoint = {
  method: string; path: string; responseKind: ResponseKind;
  requestKind: 'json' | 'multipart';
  multipartFields: readonly { name: string; required: boolean; binary: boolean }[];
  pathParameters: readonly Parameter[]; queryParameters: readonly Parameter[];
  queryMode?: 'retrieval-status';
};

function requestBody(endpoint: Endpoint, value: unknown): BodyInit | undefined {
  if (endpoint.requestKind === 'json') return value === undefined ? undefined : JSON.stringify(value);
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new TypeError('Multipart body required');
  const fields = value as Record<string, unknown>;
  const declared = new Set(endpoint.multipartFields.map(field => field.name));
  if (Object.keys(fields).some(name => !declared.has(name))) throw new TypeError('Undeclared multipart field');
  const form = new FormData();
  for (const field of endpoint.multipartFields) {
    const item = Object.hasOwn(fields, field.name) ? fields[field.name] : undefined;
    if (item === undefined || item === null) {
      if (field.required) throw new TypeError(`Missing multipart field: ${field.name}`);
      continue;
    }
    if (field.binary) {
      if (!(item instanceof Blob)) throw new TypeError(`Binary file required: ${field.name}`);
      form.append(field.name, item);
    } else {
      if (typeof item !== 'string') throw new TypeError(`String form field required: ${field.name}`);
      form.append(field.name, item);
    }
  }
  return form;
}

function parameterValue(parameter: Parameter, value: Scalar): string | undefined {
  if (value === undefined || value === null) {
    if (parameter.required) throw new TypeError(`Missing required parameter: ${parameter.name}`);
    return undefined;
  }
  const expected = parameter.type === 'integer' ? 'number' : parameter.type;
  if (typeof value !== expected) throw new TypeError(`Invalid parameter type: ${parameter.name}`);
  if (typeof value === 'number' && (!Number.isFinite(value)
      || (parameter.type === 'integer' && !Number.isSafeInteger(value))
      || (parameter.minimum !== undefined && value < parameter.minimum)
      || (parameter.maximum !== undefined && value > parameter.maximum)
      || (parameter.exclusiveMinimum !== undefined && value <= parameter.exclusiveMinimum)
      || (parameter.exclusiveMaximum !== undefined && value >= parameter.exclusiveMaximum))) {
    throw new TypeError(`Invalid numeric parameter: ${parameter.name}`);
  }
  return String(value);
}

function parameterEntries(definitions: readonly Parameter[], values: Record<string, Scalar> = {}): [string, string][] {
  const allowed = new Set(definitions.map(parameter => parameter.name));
  for (const name of Object.keys(values)) {
    if (!allowed.has(name)) throw new TypeError(`Undeclared parameter: ${name}`);
  }
  return definitions.flatMap(parameter => {
    const value = parameterValue(parameter, Object.hasOwn(values, parameter.name) ? values[parameter.name] : undefined);
    return value === undefined ? [] : [[parameter.name, value] as [string, string]];
  });
}

export function createApiClient(transport: ApiTransport) {
  return function request<K extends EndpointKey>(operation: K, ...args: ApiArgs<K>): Promise<ApiResponse<K>> {
    const endpoint: Endpoint = API_ENDPOINTS[operation];
    const parameters = (args[2] ?? {}) as UrlParameters;
    if (endpoint.queryMode === 'retrieval-status') {
      const query = parameters.query ?? {};
      if ((Object.hasOwn(query, 'scope_refs') && (Object.hasOwn(query, 'cursor') || Object.hasOwn(query, 'limit')))
          || Object.values(query).some(value => value === null)
          || (Object.hasOwn(query, 'scope_refs') && typeof query.scope_refs !== 'string')) {
        throw new TypeError('Scope status and overview parameters cannot be mixed or null');
      }
    }
    const paths = new Map(parameterEntries(endpoint.pathParameters, parameters.path));
    const path = endpoint.path.replace(/\{([^{}]+)\}/g, (_match, name: string) => encodeURIComponent(paths.get(name)!));
    const query = new URLSearchParams(parameterEntries(endpoint.queryParameters, parameters.query)).toString();
    const body = requestBody(endpoint, args[0]);
    return transport(path + (query ? `?${query}` : ''), {
      method: endpoint.method,
      ...(body !== undefined ? { body } : {}),
      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),
    }, endpoint.responseKind) as Promise<ApiResponse<K>>;
  };
}
