// Generated from PRODUCT_DESIGN.md v3.0.2 and runtime OpenAPI; do not edit.
// spec_sha256: 537239aa30315170b2a177b74a5dfca026397fdc0e15ab14a094a8b14f7c51d9
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
