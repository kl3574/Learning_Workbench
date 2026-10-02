// Generated from PRODUCT_DESIGN.md v3.0.9 and actual runtime OpenAPI.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98
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
