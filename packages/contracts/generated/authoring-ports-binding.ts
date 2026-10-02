// Generated from PRODUCT_DESIGN.md v3.0.12 and actual runtime OpenAPI.
// spec_sha256: 1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7
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
