// Generated from PRODUCT_DESIGN.md v3.0.8 and actual runtime OpenAPI.
// spec_sha256: 608b4421757dce60677353336519383307df22bf99eb4d6598bf89def6f6fcfa
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
