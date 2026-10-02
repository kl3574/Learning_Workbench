// Generated from PRODUCT_DESIGN.md v3.0.9 and actual runtime OpenAPI.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98
import type { AuthoringGroupApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
export interface AuthoringGroupRuntimeDTOMap extends AuthoringGroupApplicationDTOMap {
  AuthoringGroupPrepareWrite: Api.AuthoringGroupPrepareWrite;
  AuthoringGroupDraftView: Api.AuthoringGroupDraftView;
  AuthoringPrivateSolutionView: Api.AuthoringPrivateSolutionView;
  AuthoringGroupNumericPreviewWrite: Api.AuthoringGroupNumericPreviewWrite;
  AuthoringGroupNumericCheckView: Api.AuthoringGroupNumericCheckView;
  NumericCheckDecisionAck: Api.NumericCheckDecisionAck;
  ApprovalDecision: Api.ApprovalDecision;
}
