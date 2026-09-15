import type { ProviderPort } from './providerClient'

type Query = Parameters<ProviderPort['consents']>[0]
type MustBeFalse<Value extends false> = Value

/** Compilation must fail if the actual client query widens the application port. */
export type ProviderQueryRejectsMixedIdLimit = MustBeFalse<{ consent_id: string; limit: number } extends Query ? true : false>
export type ProviderQueryRejectsMixedIdCursor = MustBeFalse<{ consent_id: string; cursor: string } extends Query ? true : false>
export type ProviderQueryRejectsNullId = MustBeFalse<{ consent_id: null } extends Query ? true : false>
export type ProviderQueryRejectsNullCursor = MustBeFalse<{ cursor: null } extends Query ? true : false>
