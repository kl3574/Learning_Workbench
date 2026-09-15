// Generated from PRODUCT_DESIGN.md v3.0.3 and runtime OpenAPI; do not edit.
// spec_sha256: a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
