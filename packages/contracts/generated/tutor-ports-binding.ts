// Generated from PRODUCT_DESIGN.md v3.0.7; do not edit.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d

import type { TutorApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type { TutorSSEEvent } from "./tutor-sse";
export type { TutorSSEEvent } from "./tutor-sse";
// Generated from PRODUCT_DESIGN.md v3.0.7. DO NOT EDIT.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
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
