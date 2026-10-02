// Generated from PRODUCT_DESIGN.md v3.0.12 and runtime OpenAPI; do not edit.
// spec_sha256: 1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
