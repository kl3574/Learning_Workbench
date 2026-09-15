// Generated from PRODUCT_DESIGN.md v3.0.3. DO NOT EDIT.
// spec_sha256: a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8
// JSON Schema is the type source; runtime semantic checks remain required.

export type Citation = {
  "id": string;
  "title": string;
  "url"?: (string | null);
  "locator": string;
  "source_sha256"?: (string | null);
  "verification": "verified" | "unverified" | "user_supplied";
};

export type ContentRef = {
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type RetrievalAlgorithmVersions = {
  "resource": "retrieval-resource-v1";
  "normalization": "nfc-v1";
  "tokenizer": "lexical-han-gram-v1";
  "unicode": "15.0.0";
  "ranking": "scope-coverage-v1";
  "locator": "whole-block-v1";
};

export type RetrievalBlockDescriptor = {
  "ref": ContentRef;
  "title": string;
  "body_sha256": string;
  "body_bytes": number;
  "provenance": RetrievalProvenance;
  "source_descriptor_sha256": string;
  "parent_paths": Array<RetrievalScopePath>;
};

export type RetrievalBlockMaterial = {
  "scope_sha256": string;
  "corpus_sha256": string;
  "ref": ContentRef;
  "body_sha256": string;
  "body": RetrievalBodyBytes;
};

export type RetrievalCorpusDescriptor = {
  "version": "retrieval-corpus-v1";
  "workspace_id": string;
  "scope_sha256": string;
  "scope_refs": Array<ContentRef>;
  "graph": Array<RetrievalRefState>;
  "blocks": Array<RetrievalBlockDescriptor>;
  "versions": RetrievalAlgorithmVersions;
};

export type RetrievalProvenance = {
  "state": "frozen" | "unresolved";
  "original": (RetrievalRetainedSource | null);
  "citations": Array<Citation>;
  "unresolved_citation_ids": Array<string>;
  "warnings": Array<Warning>;
};

export type RetrievalRefState = {
  "ref": ContentRef;
  "current_ref": ContentRef;
  "lifecycle": "active" | "archived";
};

export type RetrievalRetainedSource = {
  "id": string;
  "media_type": string;
  "size": number;
  "sha256": string;
  "rights": string;
  "parser_version": (string | null);
};

export type RetrievalScopePath = {
  "root_ref": ContentRef;
  "course_ref": (ContentRef | null);
  "course_title": (string | null);
  "lesson_ref": (ContentRef | null);
  "lesson_title": (string | null);
  "block_ref": ContentRef;
};

export type RetrievalScopeSnapshot = {
  "descriptor": RetrievalCorpusDescriptor;
  "corpus_sha256": string;
};

export type Warning = {
  "code": string;
  "message": string;
  "locator"?: (string | null);
  "severity": "info" | "warning" | "error";
};

export type RetrievalBodyBytes = Uint8Array;
