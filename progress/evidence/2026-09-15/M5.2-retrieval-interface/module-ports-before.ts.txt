/** Target dependency ports, not implemented adapters. Transport DTOs are generated
 * from generated JSON Schema during M0; here DTO maps are generic parameters
 * to avoid maintaining a second hand-written version of every domain type. */
export type Entity = 'course'|'lesson'|'block'|'concept'|'route'|'question'|'practice_set'|'assessment'|'note';
export interface ContentRef {entity: Entity; id: string; revision: number; sha256: string}
export interface AuthContext {workspaceId: string; actorId: string; role: 'learner'|'author'; sessionId: string}
export interface WriteContext extends AuthContext {idempotencyKey: string; expectedRevision?: number}
export interface DTOMap {
 Course: unknown; Lesson: unknown; ContentBlock: unknown; Route: unknown;
 QuestionPublic: unknown; PracticeSet: unknown; AttemptCreate: unknown; AttemptPublic: unknown;
 ResponsesWrite: unknown; GradingResult: unknown; TutorRequest: unknown; ContextSnapshot: unknown;
 RunSnapshot: unknown; RunEvent: unknown; Note: unknown; Evidence: unknown;
 Recommendation: unknown; AuthoringRequest: unknown; ReviewReceipt: unknown;
 GenerationInput: unknown; ProviderEvent: unknown; LearnerProfile: unknown; WorkbenchSession: unknown;
 ProviderCapabilities: unknown; ApprovalDecision: unknown; LearningEvent: unknown;
}
export interface Page<T> {items: T[]; next_cursor: string|null; total_hint?: number}
export interface JobRef {id: string; status: 'queued'|'running'|'awaiting_approval'|'completed'|'failed'|'cancelled'}
export interface ProposedAction {id: string; kind: 'generate'|'revise'|'export'; summary: string; operation_sha256: string}
export interface PolicyPort {
 check(context: AuthContext, action: string, refs: readonly ContentRef[]): Promise<void>;
 activeAssessment(context: AuthContext): Promise<{attemptId:string; mode:'independent'|'assisted'|'open_book'}|null>;
}
export interface IngestionPort {
 stage(ctx: WriteContext, file: {name:string; bytes:Uint8Array; mediaType:string}): Promise<JobRef>;
 preview(ctx: AuthContext, importId: string): Promise<{warnings: string[]; candidateIds: string[]; inputSha256:string}>;
 commit(ctx: WriteContext, importId: string, expectedInputSha256:string): Promise<ContentRef[]>;
}
export interface ContentPort<D extends DTOMap> {
 getCourse(ctx:AuthContext, ref:ContentRef):Promise<D['Course']>;
 getLesson(ctx:AuthContext, ref:ContentRef):Promise<D['Lesson']>;
 getBlock(ctx:AuthContext, ref:ContentRef):Promise<D['ContentBlock']>;
 createDraft(ctx:WriteContext, base:ContentRef|null):Promise<{draftId:string;revision:number}>;
 publish(ctx:WriteContext, ref:ContentRef, receiptId:string):Promise<ContentRef>;
}
export interface RoutePort<D extends DTOMap> {
 save(ctx:WriteContext, route:D['Route']):Promise<ContentRef>;
 completeStep(ctx:WriteContext, route:ContentRef, stepId:string):Promise<void>;
}
export interface PracticePort<D extends DTOMap> {
 start(ctx:WriteContext, ref:ContentRef):Promise<{id:string;questions:D['QuestionPublic'][]}>;
 save(ctx:WriteContext, id:string, responses:D['ResponsesWrite']):Promise<number>;
 reveal(ctx:WriteContext, id:string, questionId:string, kind:'hint'|'solution'):Promise<{markdown:string;exposureEventId:string}>;
}
export interface AssessmentPort<D extends DTOMap> {
 start(ctx:WriteContext, request:D['AttemptCreate']):Promise<D['AttemptPublic']>;
 save(ctx:WriteContext, attemptId:string, responses:D['ResponsesWrite']):Promise<number>;
 submit(ctx:WriteContext, attemptId:string):Promise<D['AttemptPublic']>;
 result(ctx:AuthContext, attemptId:string):Promise<D['GradingResult']>;
}
export interface RetrievalHit {ref:ContentRef; text:string; locator:string; score:number}
export interface RetrievalPort {query(ctx:AuthContext, q:string, scope:ContentRef[], limit:number):Promise<RetrievalHit[]>}
export interface ContextPort<D extends DTOMap> {freeze(ctx:AuthContext, request:D['TutorRequest']):Promise<D['ContextSnapshot']>}
export interface TutorPort<D extends DTOMap> {
 start(ctx:WriteContext, request:D['TutorRequest']):Promise<D['RunSnapshot']>;
 events(ctx:AuthContext, runId:string, afterSeq:number, signal:AbortSignal):AsyncIterable<D['RunEvent']>;
 cancel(ctx:WriteContext, runId:string):Promise<D['RunSnapshot']>;
}
export interface ProviderPort<D extends DTOMap> {
 capabilities():Promise<D['ProviderCapabilities']>;
 generate(input:D['GenerationInput'],signal:AbortSignal):AsyncIterable<D['ProviderEvent']>;
}
export interface ProviderApplicationDTOMap {
 ProviderCapabilitiesResponse: unknown; ProviderConfigWrite: unknown; ProviderConfigView: unknown;
 ProviderConfigAck: unknown; ProviderSecretWrite: unknown; ProviderSecretAck: unknown;
 ConsentPreviewWrite: unknown; ConsentProposalView: unknown; ConsentCreate: unknown;
 ConsentCreateAck: unknown; ConsentRevoke: unknown; ConsentPage: unknown; MutationAck: unknown;
}
export type ProviderConsentQuery = {consent_id:string;cursor?:never;limit?:never}
 | {consent_id?:never;cursor?:string;limit?:number};
export interface ProviderApplicationPort<P extends ProviderApplicationDTOMap> {
 capabilities(ctx:AuthContext):Promise<P['ProviderCapabilitiesResponse']>;
 readConfig(ctx:AuthContext, providerId:string):Promise<P['ProviderConfigView']>;
 saveConfig(ctx:WriteContext, providerId:string, request:P['ProviderConfigWrite']):Promise<P['ProviderConfigAck']>;
 saveSecret(ctx:WriteContext, providerId:string, request:P['ProviderSecretWrite']):Promise<P['ProviderSecretAck']>;
 deleteSecret(ctx:WriteContext, providerId:string, expectedConfigSha256:string):Promise<P['ProviderSecretAck']>;
 preview(ctx:WriteContext, request:P['ConsentPreviewWrite']):Promise<P['ConsentProposalView']>;
 proposal(ctx:AuthContext, proposalId:string):Promise<P['ConsentProposalView']>;
 grant(ctx:WriteContext, request:P['ConsentCreate']):Promise<P['ConsentCreateAck']>;
 consents(ctx:AuthContext, query:ProviderConsentQuery):Promise<P['ConsentPage']>;
 revoke(ctx:WriteContext, consentId:string, request:P['ConsentRevoke']):Promise<P['MutationAck']>;
}
export interface LearningPort<D extends DTOMap> {
 recordUserAction(ctx:WriteContext, action:'read_marked'|'note_created', ref:ContentRef):Promise<void>;
 evidence(ctx:AuthContext, conceptId:string):Promise<D['Evidence'][]>;
}
export interface RecommendationDTOMap {
 RecommendationPage: unknown; RecommendationDecisionWrite: unknown; MutationAck: unknown;
}
export interface RecommendationPort<R extends RecommendationDTOMap> {
 read(ctx:AuthContext, query:{courseId?:string;recommendationId?:string;cursor?:string;limit?:number}):Promise<R['RecommendationPage']>;
 decide(ctx:WriteContext, id:string, request:R['RecommendationDecisionWrite'], expectedDecisionSha256:string):Promise<R['MutationAck']>;
}
export interface NotesPort<D extends DTOMap> {save(ctx:WriteContext, note:D['Note']):Promise<ContentRef>}
export interface AuthoringPort<D extends DTOMap> {
 generate(ctx:WriteContext, request:D['AuthoringRequest']):Promise<JobRef>;
 review(ctx:WriteContext, ref:ContentRef):Promise<D['ReviewReceipt']>;
}
export interface CodexBrokerPort<D extends DTOMap> {
 start(ctx:WriteContext, sandboxRootId:string):Promise<{sessionId:string}>;
 turn(ctx:WriteContext, sessionId:string, prompt:string):Promise<JobRef>;
 decide(ctx:WriteContext, approvalId:string, decision:D['ApprovalDecision']):Promise<void>;
 importArtifacts(ctx:WriteContext, jobId:string, approvedPaths:string[]):Promise<JobRef>;
}
export interface WorkspacePort {
 export(ctx:WriteContext, profile:'learner'|'author'|'full_backup'):Promise<JobRef>;
 restorePreview(ctx:WriteContext, backupSha256:string):Promise<{proposalId:string;warnings:string[]}>;
 restoreCommit(ctx:WriteContext, proposalId:string):Promise<JobRef>;
}
export interface ConnectorPort {
 preview(ctx:AuthContext):Promise<ProposedAction[]>;
 apply(ctx:WriteContext, approvedActionId:string, operationSha256:string):Promise<JobRef>;
}

export interface SearchPort {search(ctx:WriteContext, request:{query:string;consentId:string;maxSources:number}, signal:AbortSignal):Promise<{executed:boolean;sources:{id:string;url:string;title:string;retrievedAt:string;excerpt:string}[]}>}
export interface ProfilePort<D extends DTOMap> {read(ctx:AuthContext):Promise<D['LearnerProfile']>;save(ctx:WriteContext, profile:D['LearnerProfile']):Promise<D['LearnerProfile']>}
export interface WorkbenchSessionPort<D extends DTOMap> {read(ctx:AuthContext):Promise<D['WorkbenchSession']>;save(ctx:WriteContext, snapshot:D['WorkbenchSession']):Promise<D['WorkbenchSession']>}
