// Generated from PRODUCT_DESIGN.md v3.0.14 and runtime OpenAPI; do not edit.
// spec_sha256: bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
