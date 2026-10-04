// Generated from PRODUCT_DESIGN.md v3.0.15 and actual runtime OpenAPI.
// spec_sha256: b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec
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
