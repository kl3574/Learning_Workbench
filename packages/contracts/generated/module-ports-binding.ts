// Generated from PRODUCT_DESIGN.md v3.0.14; do not edit.
// spec_sha256: bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144
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
