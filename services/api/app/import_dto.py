"""Strict M2.2 inline DTOs from PRODUCT_DESIGN Appendix A; no private answers."""

from typing import Literal

from fastapi import UploadFile
from pydantic import Field, model_validator

from packages.contracts import domain_models as dm

ImportKind = Literal["auto", "markdown", "text", "html", "pdf", "docx", "learnpack"]
ImportStatus = Literal["staged", "parsing", "preview_ready", "committed", "cancelled", "failed"]
JobStatus = Literal["queued", "running", "awaiting_approval", "completed", "failed", "cancelled"]


class ImportUpload(dm.StrictModel):
    file: UploadFile
    kind: ImportKind
    target_course_id: dm.Id | None = None


class ImportStaged(dm.StrictModel):
    import_id: dm.Id
    job: dm.JobRef
    input_sha256: dm.Sha256


class CandidateSummary(dm.StrictModel):
    course_title: str
    lesson_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    unresolved_refs: list[str]


class ImportPreview(dm.StrictModel):
    id: dm.Id
    status: ImportStatus
    input_sha256: dm.Sha256
    warnings: list[dm.Warning]
    candidate_summary: CandidateSummary
    preview_refs: list[dm.Id]


class ImportIdMapping(dm.StrictModel):
    old_id: dm.Id
    new_id: dm.Id


class ImportCommitRequest(dm.StrictModel):
    expected_input_sha256: dm.Sha256
    accepted_warning_codes: list[str] = Field(max_length=2000)
    id_mapping: list[ImportIdMapping] = Field(max_length=2000)

    @model_validator(mode="after")
    def unique_decisions(self) -> "ImportCommitRequest":
        if len(set(self.accepted_warning_codes)) != len(self.accepted_warning_codes):
            raise ValueError("Warning decisions must be unique.")
        for field in ("old_id", "new_id"):
            identifiers = [getattr(item, field) for item in self.id_mapping]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError("ID mappings must be one-to-one.")
        return self


class ImportCommitResponse(dm.StrictModel):
    course_refs: list[dm.ContentRef]
    migration_receipt_id: dm.Id


class ImportCancelRequest(dm.StrictModel):
    expected_input_sha256: dm.Sha256


class ImportCancelResponse(dm.StrictModel):
    id: dm.Id
    status: Literal["cancelled"] = "cancelled"


class JobProgress(dm.StrictModel):
    completed: int = Field(ge=0)
    total: int | None = Field(ge=0)
    label: str

    @model_validator(mode="after")
    def bounded_progress(self) -> "JobProgress":
        if self.total is not None and self.completed > self.total:
            raise ValueError("Completed work cannot exceed the known total.")
        return self


class JobSnapshot(dm.StrictModel):
    id: dm.Id
    workspace_id: dm.Id
    kind: str
    status: JobStatus
    revision: dm.Revision
    created_at: dm.UTC
    updated_at: dm.UTC
    progress: JobProgress
    result_refs: list[dm.ContentRef]
    warnings: list[dm.Warning]
    error: dm.ErrorDetail | None

    @model_validator(mode="after")
    def no_premature_results(self) -> "JobSnapshot":
        if self.status != "completed" and self.result_refs:
            raise ValueError("Only a completed job may publish result references.")
        return self


class JobCancelRequest(dm.StrictModel):
    expected_revision: dm.Revision


class DownloadArtifact(dm.StrictModel):
    artifact_id: dm.Id
    filename: str = Field(min_length=1, max_length=240)
    size: int = Field(ge=0)
    sha256: dm.Sha256
    media_type: str
    download_path: str

    @model_validator(mode="after")
    def controlled_download(self) -> "DownloadArtifact":
        if self.download_path != f"/api/v1/artifacts/{self.artifact_id}/download":
            raise ValueError("Downloads must use the exact controlled same-origin endpoint.")
        if any(ord(char) < 32 or ord(char) == 127 or char in "/\\" for char in self.filename):
            raise ValueError("Artifact filename must not contain a path or control characters.")
        return self


class SourceResponse(dm.StrictModel):
    id: dm.Id
    media_type: str
    size: int = Field(ge=0)
    sha256: dm.Sha256
    rights: str
    parser_version: str | None
    warnings: list[dm.Warning]
    artifact: DownloadArtifact


class BlockDraftPayload(dm.StrictModel):
    metadata: dm.ContentBlock
    body_markdown: str
    source_id: dm.Id


DraftPayload = (BlockDraftPayload | dm.Course | dm.Lesson | dm.Concept | dm.Route
                | dm.QuestionPublic | dm.PracticeSet | dm.AssessmentBlueprint | dm.Note)


class ImportDraftSnapshot(dm.StrictModel):
    id: dm.Id
    kind: dm.Entity
    revision: dm.Revision
    base_ref: dm.ContentRef | None
    state: Literal["draft", "in_review", "approved", "needs_changes", "published", "cancelled"]
    candidate_sha256: dm.Sha256
    payload: DraftPayload
    warnings: list[dm.Warning]

    @model_validator(mode="after")
    def kind_matches_payload(self) -> "ImportDraftSnapshot":
        entity = "block" if isinstance(self.payload, BlockDraftPayload) else self.payload.entity
        if self.kind != entity:
            raise ValueError("A draft must carry the specialized payload for its kind.")
        return self
