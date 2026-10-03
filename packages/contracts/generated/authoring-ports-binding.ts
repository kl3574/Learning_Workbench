// Generated from PRODUCT_DESIGN.md v3.0.14 and actual runtime OpenAPI.
// spec_sha256: bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144
import type { AuthoringApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
export interface AuthoringRuntimeDTOMap extends AuthoringApplicationDTOMap {
  AuthoringPrepareWrite: Api.AuthoringPrepareWrite;
  AuthoringJobPage: Api.AuthoringJobPage;
  AuthoringJobView: Api.AuthoringJobView;
  AuthoringDraftView: Api.AuthoringDraftView;
  AuthoringJobReadView: Api.AuthoringJobReadView;
  NumericCheckPreviewWrite: Api.NumericCheckPreviewWrite;
  NumericCheckView: Api.NumericCheckView;
  NumericCheckDecisionAck: Api.NumericCheckDecisionAck;
  ApprovalDecision: Api.ApprovalDecision;
}
