// Generated from PRODUCT_DESIGN.md v3.0.7; do not edit.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
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
