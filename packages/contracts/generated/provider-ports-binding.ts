// Generated from PRODUCT_DESIGN.md v3.0.11 and runtime OpenAPI; do not edit.
// spec_sha256: 35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29
import type { ProviderApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";

export type { ProviderConsentQuery } from "../module-ports";

export interface ProviderRuntimeDTOMap extends ProviderApplicationDTOMap {
  ProviderCapabilitiesResponse: Api.ProviderCapabilitiesResponse;
  ProviderConfigWrite: Api.ProviderConfigWrite;
  ProviderConfigView: Api.ProviderConfigView;
  ProviderConfigAck: Api.ProviderConfigAck;
  ProviderSecretWrite: Api.ProviderSecretWrite;
  ProviderSecretAck: Api.ProviderSecretAck;
  ConsentPreviewWrite: Api.ConsentPreviewWrite;
  ConsentProposalView: Api.ConsentProposalView;
  ConsentCreate: Api.ConsentCreate;
  ConsentCreateAck: Api.ConsentCreateAck;
  ConsentRevoke: Api.ConsentRevoke;
  ConsentPage: Api.ConsentPage;
  MutationAck: Api.MutationAck;
}
