// Generated from PRODUCT_DESIGN.md v3.0.6; do not edit.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924

import type { TutorApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type { TutorSSEEvent } from "./tutor-sse";
export type { TutorSSEEvent } from "./tutor-sse";
// Generated from PRODUCT_DESIGN.md v3.0.6. DO NOT EDIT.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
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
