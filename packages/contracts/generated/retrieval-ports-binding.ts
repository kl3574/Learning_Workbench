// Generated from PRODUCT_DESIGN.md v3.0.15 and real registered contracts; do not edit.
// spec_sha256: b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec
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
