// Generated from PRODUCT_DESIGN.md v3.0.5 and runtime OpenAPI; do not edit.
// spec_sha256: 2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37
import type { RecommendationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {
  RecommendationPage: Api.RecommendationPage;
  RecommendationDecisionWrite: Api.RecommendationDecisionWrite;
  MutationAck: Api.MutationAck;
}
