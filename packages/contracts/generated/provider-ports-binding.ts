// Generated from PRODUCT_DESIGN.md v3.0.5 and runtime OpenAPI; do not edit.
// spec_sha256: 2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37
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
