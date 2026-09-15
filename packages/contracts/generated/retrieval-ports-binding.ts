// Generated from PRODUCT_DESIGN.md v3.0.4 and real registered contracts; do not edit.
// spec_sha256: 9cc5adbe72edfc993b5d5e99dcb3f9436e475ab2be4dd58e83f72e3104353b9c
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
