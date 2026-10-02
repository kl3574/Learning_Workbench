// Generated from PRODUCT_DESIGN.md v3.0.9; do not edit.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98
import type { DTOMap } from "../module-ports";
import type * as Model from "./types";

export interface DomainDTOMap extends DTOMap {
  Course: Model.Course;
  Lesson: Model.Lesson;
  ContentBlock: Model.ContentBlock;
  Route: Model.Route;
  QuestionPublic: Model.QuestionPublic;
  PracticeSet: Model.PracticeSet;
  AttemptCreate: Model.AttemptCreate;
  AttemptPublic: Model.AttemptPublic;
  ResponsesWrite: Model.ResponsesWrite;
  GradingResult: Model.GradingResult;
  TutorRequest: Model.TutorRequest;
  ContextSnapshot: Model.ContextSnapshot;
  RunSnapshot: Model.RunSnapshot;
  RunEvent: Model.RunEvent;
  Note: Model.Note;
  Evidence: Model.Evidence;
  Recommendation: Model.Recommendation;
  AuthoringRequest: Model.AuthoringRequest;
  ReviewReceipt: Model.ReviewReceipt;
  GenerationInput: Model.GenerationInput;
  ProviderEvent: Model.ProviderEvent;
  LearnerProfile: Model.LearnerProfile;
  WorkbenchSession: Model.WorkbenchSession;
  ProviderCapabilities: Model.ProviderCapabilities;
  ApprovalDecision: Model.ApprovalDecision;
  LearningEvent: Model.LearningEvent;
}
