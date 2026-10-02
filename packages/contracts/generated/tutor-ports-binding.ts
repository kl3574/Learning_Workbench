// Generated from PRODUCT_DESIGN.md v3.0.9; do not edit.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98

import type { TutorApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type { TutorSSEEvent } from "./tutor-sse";
export type { TutorSSEEvent } from "./tutor-sse";
// Generated from PRODUCT_DESIGN.md v3.0.9. DO NOT EDIT.
// spec_sha256: a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98
// JSON Schema is the type source; runtime semantic checks remain required.

export type TutorEventsQuery = {
  "after_seq"?: number;
};

export type TutorPageQuery = {
  "cursor"?: string;
  "limit"?: number;
};

export interface TutorRuntimeDTOMap extends TutorApplicationDTOMap {
  TutorThreadCreate: Api.TutorThreadCreate;
  TutorThreadView: Api.TutorThreadView;
  TutorPageQuery: TutorPageQuery;
  TutorThreadPage: Api.TutorThreadPage;
  TutorMessagePage: Api.TutorMessagePage;
  TutorRunCreate: Api.TutorRunCreate;
  TutorRunView: Api.TutorRunView;
  TutorRunCancel: Api.TutorRunCancel;
  TutorRunControlView: Api.TutorRunControlView;
  TutorEventsQuery: TutorEventsQuery;
  TutorSSEEvent: TutorSSEEvent;
}
