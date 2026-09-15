// Generated from PRODUCT_DESIGN.md v3.0.1 and runtime OpenAPI; do not edit.
// spec_sha256: 397829f5267248aedfc60faf7cacbb12669966b1c1d636a909b04189e0cc09dd
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
