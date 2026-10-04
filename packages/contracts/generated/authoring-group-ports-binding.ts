// Generated from PRODUCT_DESIGN.md v3.0.14 and actual runtime OpenAPI.
// spec_sha256: bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144
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
