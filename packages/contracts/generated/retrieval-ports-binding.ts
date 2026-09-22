// Generated from PRODUCT_DESIGN.md v3.0.7 and real registered contracts; do not edit.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
import type { RetrievalApplicationDTOMap, ContentRetrievalDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type * as Content from "./retrieval-content-types";

export type RetrievalIndexStatusQuery =
  | { scope_refs: string; cursor?: never; limit?: never }
  | { scope_refs?: never; cursor?: string; limit?: number };
export type RetrievalIndexStatusView = Api.RetrievalIndexScopeStatus | Api.RetrievalIndexOverview;

export interface RetrievalRuntimeDTOMap extends RetrievalApplicationDTOMap {
  RetrievalIndexRebuildWrite: Api.RetrievalIndexRebuildWrite;
  RetrievalQueryView: Api.RetrievalQueryView;
  RetrievalQueryWrite: Api.RetrievalQueryWrite;
  RetrievalIndexStatusQuery: RetrievalIndexStatusQuery;
  RetrievalIndexStatusView: RetrievalIndexStatusView;
}

export interface ContentRetrievalRuntimeDTOMap extends ContentRetrievalDTOMap {
  RetrievalBlockMaterial: Content.RetrievalBlockMaterial;
  RetrievalScopeSnapshot: Content.RetrievalScopeSnapshot;
}
