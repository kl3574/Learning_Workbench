// Generated from PRODUCT_DESIGN.md v3.0.14 and real registered contracts; do not edit.
// spec_sha256: bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144
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
