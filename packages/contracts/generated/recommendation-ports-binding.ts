// Generated from PRODUCT_DESIGN.md v3.0.13 and runtime OpenAPI; do not edit.
// spec_sha256: 949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
