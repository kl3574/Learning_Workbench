// Generated from PRODUCT_DESIGN.md v3.0.6 and real registered contracts; do not edit.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
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
