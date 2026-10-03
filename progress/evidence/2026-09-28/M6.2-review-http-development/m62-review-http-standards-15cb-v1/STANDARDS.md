# Standards

No blocking Standards finding in `ba8fa724...15cb6088` (10 files, four commits). Sole documented authority is PRODUCT_DESIGN.md; AGENTS.md points only to it. Tool-enforced lint/type rules were not re-reviewed as manual findings.

The added HTTP adapter delegates commands and reads to Quality application ports; it does not access another module's tables (spec:349). Production composition binds real import/single/group candidate owners, existing numeric-history owners, the real ReviewWorker and explicit `(profile, job kind)` artifact readers. Startup and shutdown register the new worker symmetrically without substituting a placeholder.

`jobs.py:94–95,133–145` adds only explicit injected ReviewService dispatch. Independent AST comparison confirms every previous owner branch is unchanged, including version-sensitive single/group Authoring and numeric routing, Grading, Import, Retrieval, Tutor and missing-job handling. Unknown kinds retain their prior unavailable result. Original safe-control delegation is preserved for existing consumers.

`import_http.py:37–41` permits the composed Jobs/Artifacts services while preserving the standalone defaults. Registered import readers remain present beside the exact Quality report reader; download adds no-store/Cookie variance and retains the actual owner download. The report route does not turn routing metadata into permission.

The fixed generated OpenAPI JSON adds exactly three paths and five DTO schemas; every prior path and schema is unchanged as parsed JSON. Typed client/coverage follow the same three operations, with product_acceptance still NOT_RUN (spec:964–966, R-29). Synthetic tests explicitly preserve mathematical/source/pedagogy NOT_RUN and do not claim human approval. No actionable baseline smell outweighs these explicit boundaries.

Read-only evidence verification: author related gate172PASS/2dependency warnings, RuffPASS, mypy195PASS and specPASS; all four stages'989 before/after engineering inputs independently match every fixed Git blob and log hashes. Reviewer did not rerun tests. This review covers this fixed HTTP slice, not later privacy/workflow increments or full product acceptance.
