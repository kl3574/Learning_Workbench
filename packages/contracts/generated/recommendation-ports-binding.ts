// Generated from PRODUCT_DESIGN.md v3.0.8 and runtime OpenAPI; do not edit.
// spec_sha256: 608b4421757dce60677353336519383307df22bf99eb4d6598bf89def6f6fcfa
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
