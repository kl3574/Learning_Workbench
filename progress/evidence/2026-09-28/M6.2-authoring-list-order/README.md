# Authoring list response ordering

Original fixed RED236fbc93dce481ca31943fb4e0a643cefd1ecfbe, final f18c92c1ad74598a70b731ce9caf241e40d8e841, integrated as8507d09. Only the list hook and permanent focused test change. Older requests and effect cleanup cannot decode or replace newer list/active Job/cursor state. No deadline, command ACK, Policy or generated-code change.

Two real ordering failures plus one control preceded five permanent passing cases; all63Authoring tests/11files and strict TS passed. The old CI case passed once locally before and once after this change. The reproduced stale-response case had busy=false; the historical CI screenshot had busy=true. A held-Promise diagnostic shows the latter shape is possible but does not identify the CI cause. Original native module-config failure is retained. No full native success is inferred.

This package includes all diagnostic text/code/source manifests and the independent root review (no test rerun). Native screenshots and produced native-output JSON remain private and are explicitly enumerated with original hashes under excluded_raw. References to them in the report are not claims they are bundled here. Only literal path substitutions; full selected original logs including RED/config failures are retained.
