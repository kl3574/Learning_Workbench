# e399 grant narrow static closure

Fixed `e399a66f85e701207d469511f9726abfc5fa2069` relative to f36. The delta changes two production files by two lines each and adds two regression tests (four parameterized cases) to one existing test file. Sole v3.0.15 is unchanged.

Both f36 P2 findings are CLOSED_STATIC. `provider_codex_consents.py:237–238` compares the durable grant timestamp to the original expiry before appending any event, returning normal `CODEX_CONSENT_EXPIRED`; original ACK replay remains earlier and unchanged. `codex_turn_repository.py:129–130` rejects non-dict decoded JSON with the named damaged-history error before reading its version. It preserves version selection and strict decoders for valid objects, and does not broadly catch AttributeError.

The added tests use actual synthetic owner/HTTP records: one moves the grant clock across expiry and requires the correct 409 plus unchanged tables; three replace the original event JSON with array/null/integer and require damaged-history 409 for both GET and original prepare replay, again unchanged tables. This peer inspected these fixed test bytes and their production paths but executed none of them. Owner's separately reported REDs and ongoing/final gates retain their own provenance; this receipt does not claim to have run or fully audited them.

No additional confirmed Standards or Spec blocker in this narrow delta. Original f36 OPEN record is preserved. This closure is not production model proof, a start/dispatch acceptance, an approval/artifact implementation or whole-M6.3 success. Share only the explicit safe and outer lists.
