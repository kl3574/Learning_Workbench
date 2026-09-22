// Generated from PRODUCT_DESIGN.md v3.0.7 and actual runtime OpenAPI.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
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
