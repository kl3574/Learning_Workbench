// Generated from PRODUCT_DESIGN.md v3.0.6 and runtime OpenAPI; do not edit.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
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
