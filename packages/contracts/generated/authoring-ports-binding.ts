// Generated from PRODUCT_DESIGN.md v3.0.6 and actual runtime OpenAPI.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
import type { AuthoringApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
export interface AuthoringRuntimeDTOMap extends AuthoringApplicationDTOMap {
  AuthoringPrepareWrite: Api.AuthoringPrepareWrite;
  AuthoringJobPage: Api.AuthoringJobPage;
  AuthoringJobView: Api.AuthoringJobView;
  AuthoringDraftView: Api.AuthoringDraftView;
  NumericCheckPreviewWrite: Api.NumericCheckPreviewWrite;
  NumericCheckView: Api.NumericCheckView;
  NumericCheckDecisionAck: Api.NumericCheckDecisionAck;
  ApprovalDecision: Api.ApprovalDecision;
}
