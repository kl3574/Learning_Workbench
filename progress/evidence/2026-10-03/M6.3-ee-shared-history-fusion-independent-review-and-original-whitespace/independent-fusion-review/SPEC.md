# Spec axis — v4 interrupt and v5 operation coexistence

No confirmed integration blocker under sole PRODUCT_DESIGN v3.0.15, SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec.

Read chain: repository:141-148 selects strict v5/v4/v3/v2/v1 decoders before complete hash/sequence checks. The v4 wrapper is verified at :159-163 before reducing its original inner stop command; v5 instead joins approval binding at :169-170. Existing head/member/command/interrupt completeness checks are retained (:95-158,229-232). Unknown versions still fail the strict fallback decoder, not an open dictionary.

Append chain: :425-458 chooses separate v4 and v5 envelopes, preserves the common hash/head sequence, records the outer interrupt command and its exact private stop/ACK witness, then unwraps only the v4 event. v5 updates the approval control through :493-497 without changing session CAS. _approval_bound:386-409 rejects switching an approval between v3/v5; only a v5 approved started r3 may advance to the corresponding r4 terminal witness after its control was closed. This does not reopen v3 denied operations.

Stop/late-result interaction: service request_stop remains original at :404-458. Active cancellation records a request and session revision, without inventing tool completion. The unchanged owner worker closes pending operations while the turn is still active (codex_turn_worker.py:104-125), then appends terminal Provider/Codex facts (:126-137). A started operation's unknown/late fact therefore remains representable before final active-slot release. Current control projection now receives the read transaction and complete checked approval/history context (service:125-136); its owner derives validity without executing or rewriting history. Old command ACK replay remains original repository:506-515.

Old v1/v2/v3/v4 model files are exact to7f3; the new v5 model/profile/execution and other 13 owner paths are exact to83d. This is not proof that every mixed-version concurrency sequence succeeds; the root's separately assigned real HTTP mixed regression and full combined gates remain required. No prior subset or static closure is upgraded to combined acceptance.
