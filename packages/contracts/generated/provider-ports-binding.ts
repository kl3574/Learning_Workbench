// Generated from PRODUCT_DESIGN.md v3.0.9 and runtime OpenAPI; do not edit.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98
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
