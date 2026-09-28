// Generated from PRODUCT_DESIGN.md v3.0.8; do not edit.
// spec_sha256: 608b4421757dce60677353336519383307df22bf99eb4d6598bf89def6f6fcfa

import type { TutorApplicationDTOMap } from "../module-ports";
import type * as Api from "./api-types";
import type { TutorSSEEvent } from "./tutor-sse";
export type { TutorSSEEvent } from "./tutor-sse";
// Generated from PRODUCT_DESIGN.md v3.0.8. DO NOT EDIT.
// spec_sha256: 608b4421757dce60677353336519383307df22bf99eb4d6598bf89def6f6fcfa
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
