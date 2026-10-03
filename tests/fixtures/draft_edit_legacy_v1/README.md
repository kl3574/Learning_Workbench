# Original v1 synthetic owner records

Captured from fixed source `316bf693e52f1ca08a675fc7671f4d9cebad3e8b` by two independent real local HTTP Edit fixtures. `empty-dependencies-published` ran create, PATCH, machine Review, an explicitly synthetic human decision and publication. `dependencies-no-witness-unpublished` ran create and PATCH against an original text block with two dependencies.

Record JSON files are the exact SQLite owner record bytes, with their stored digests checked during capture. ACK files are exact response body bytes obtained by replaying the original complete requests and keys; table hashes were unchanged by replay. Each directory manifest binds its raw bytes. No headers, session tokens, database copy or real teaching material are included. The synthetic decisions prove protocol behavior only.

Keep these bytes unchanged. New code must retain the no-dependency v1 JSON, hashes and ACKs. The unreleased v1 dependency records lack a frozen dependency witness and must fail closed; they must never receive a default witness or be silently rehashed as v2.
