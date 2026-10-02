// Generated from PRODUCT_DESIGN.md v3.0.11 and runtime OpenAPI; do not edit.
// spec_sha256: 35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
