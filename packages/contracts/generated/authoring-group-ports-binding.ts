// Generated from PRODUCT_DESIGN.md v3.0.7 and actual runtime OpenAPI.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
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
