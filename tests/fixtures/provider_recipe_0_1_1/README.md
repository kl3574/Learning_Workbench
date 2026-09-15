# Synthetic reference protocol events

These five JSONL files are the unchanged output of the pinned official wheel's ResponsesChunkGenerator/StreamProcessor, executed on 2026-09-15 in a network-disabled, clear-environment sandbox with invented backend chunks and reported usage. The generation script is retained as text. No model inference or real HTTP/usage occurred. Tests add their own SSE framing and byte splitting around these original semantic events.

The wheel distribution is 0.1.1 while its native version reports 0.1.0. Both are recorded separately. Matching Python entry bytes do not prove a reproducible native build or hosted deployment equivalence. Hashes and the fixed source reference are in manifest.json. Mutations used by negative tests are explicitly constructed copies, never rewritten originals.
