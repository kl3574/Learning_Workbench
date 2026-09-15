// Generated from PRODUCT_DESIGN.md v3.0.4 and runtime OpenAPI; do not edit.
// spec_sha256: 9cc5adbe72edfc993b5d5e99dcb3f9436e475ab2be4dd58e83f72e3104353b9c
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
