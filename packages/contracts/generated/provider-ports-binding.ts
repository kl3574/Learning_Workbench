// Generated from PRODUCT_DESIGN.md v3.0.7 and runtime OpenAPI; do not edit.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
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
