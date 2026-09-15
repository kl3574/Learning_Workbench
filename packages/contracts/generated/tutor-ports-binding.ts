// Generated from PRODUCT_DESIGN.md v3.0.4; do not edit.
// spec_sha256: 9cc5adbe72edfc993b5d5e99dcb3f9436e475ab2be4dd58e83f72e3104353b9c

import type { TutorApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type { TutorSSEEvent } from "./tutor-sse";
export type { TutorSSEEvent } from "./tutor-sse";
// Generated from PRODUCT_DESIGN.md v3.0.4. DO NOT EDIT.
// spec_sha256: 9cc5adbe72edfc993b5d5e99dcb3f9436e475ab2be4dd58e83f72e3104353b9c
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
