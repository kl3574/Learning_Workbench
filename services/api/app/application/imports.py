"""Staged import, explicit preview confirmation, and private source access."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
import mimetypes
import io
import zipfile
from pathlib import PurePosixPath
import sqlite3
from typing import Any

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from packages.contracts.validation import ENTITY_MODELS, PublishedModel

from ..import_dto import (
    BlockDraftPayload, CandidateSummary, DownloadArtifact, ImportCancelRequest, ImportCancelResponse,
    ImportCommitRequest, ImportCommitResponse, ImportDraftSnapshot, ImportPreview, ImportStaged,
    JobCancelRequest, JobProgress, JobSnapshot, SourceResponse,
)
from ..infrastructure.blobs import BlobStore
from ..infrastructure.content_repository import ContentRepository, damaged, missing, reference
from ..infrastructure.database import Database, utc_now
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.import_mapping import object_key, remap_import
from ..infrastructure.import_repository import ImportRepository, identifier, json_object, json_text
from ..infrastructure.provenance_repository import ProvenanceRepository
from ..infrastructure.security import SessionIdentity, guard_subject_access
from .content import ContentService
from .errors import ApiError


def invalid() -> ApiError:
    return ApiError(422, "SCHEMA_INVALID", "导入请求或存储格式无效。")


def safe_filename(filename: str) -> str:
    value = PurePosixPath(filename.replace("\\", "/")).name
    value = "".join(char for char in value if ord(char) >= 32 and ord(char) != 127).strip()[:200]
    return value if value not in {"", ".", ".."} else "import.bin"


def visibility(row: sqlite3.Row) -> str:
    metadata = json_object(row["source_metadata"])
    return str(metadata.get("visibility", "author_private"))


def preview_visibility(row: sqlite3.Row) -> str:
    metadata = json_object(row["source_metadata"])
    return str(metadata.get("preview_visibility", metadata.get("visibility", "author_private")))


class ImportService:
    def __init__(self, database: Database):
        self.database = database
        self.blobs = BlobStore(database.settings.data_dir, max_bytes=max(database.settings.max_upload_bytes, database.settings.max_package_bytes))
        self.content = ContentService(database)

    @contextmanager
    def _access(self, identity: SessionIdentity) -> Iterator[ImportRepository]:
        try:
            with self.database.transaction() as connection:
                ContentRepository(connection, identity.workspace_id).require_workspace()
                guard_subject_access(connection, identity.workspace_id)
                yield ImportRepository(connection, identity.workspace_id)
        except sqlite3.Error:
            raise ApiError(503, "IMPORT_STORAGE_UNAVAILABLE", "导入存储暂不可用。", True) from None

    @staticmethod
    def _private(identity: SessionIdentity, row: sqlite3.Row, *, pending_ok: bool = False) -> None:
        if preview_visibility(row) != "learner" and identity.role != "author":
            if pending_ok and row["status"] in {"staged", "parsing", "failed", "cancelled"}:
                return
            raise ApiError(403, "POLICY_DENIED", "此作者私有材料需要作者角色。")

    def stage(self, identity: SessionIdentity, *, data: bytes, filename: str, kind: str,
              target_course_id: str | None = None, key: str | None) -> ImportStaged:
        if type(data) is not bytes or not data or len(data) > self.database.settings.max_upload_bytes:
            raise ApiError(413, "IMPORT_SIZE_INVALID", "原件必须非空且不超过配置的大小预算。")
        if kind not in {"auto", "markdown", "text", "html", "pdf", "docx", "learnpack"}:
            raise invalid()
        filename = safe_filename(filename)
        digest = sha256_bytes(data)
        with self._access(identity) as repository:
            def operation() -> dict[str, Any]:
                target = None
                if target_course_id is not None:
                    target_value = ContentRepository(repository.connection, identity.workspace_id).current(target_course_id).value
                    if not isinstance(target_value, dm.Course):
                        raise invalid()
                    target = reference(target_value).model_dump(mode="json")
                info = self.blobs.write(data, expected_sha256=digest)
                repository.add_blob(info)
                import_id, source_id, job_id, artifact_id = (identifier(prefix) for prefix in ("import", "source", "job", "artifact"))
                from .import_parsing import detect_import_visibility
                archive_detected = zipfile.is_zipfile(io.BytesIO(data))
                raw_visibility = "author_private" if archive_detected or kind == "docx" else detect_import_visibility(data, kind, filename)
                media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                now = utc_now()
                source_metadata = {"artifact_id": artifact_id, "filename": filename, "visibility": raw_visibility,
                                   "visibility_verified": False, "warnings": [], "origin": "user_supplied"}
                repository.connection.execute(
                    "INSERT INTO sources(id,workspace_id,blob_sha256,media_type,title,rights,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (source_id, identity.workspace_id, digest, media_type, filename, "user_supplied; rights_not_verified", json_text(source_metadata), now),
                )
                job_input = {"source_id": source_id, "kind": kind, "filename": filename, "target_ref": target, "archive_detected": archive_detected, "budgets": asdict(self.database.settings.import_budgets)}
                repository.connection.execute(
                    "INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) VALUES(?,?,'import','queued',1,?,?,?,?)",
                    (job_id, identity.workspace_id, digest, json_text(job_input), now, now),
                )
                repository.artifact(info=info, filename=filename, media_type=media_type, visibility=raw_visibility,
                                    profile="import_original", job_id=job_id, artifact_id=artifact_id)
                repository.connection.execute(
                    "INSERT INTO ingestion_imports(id,workspace_id,source_id,job_id,input_sha256,status,created_at) VALUES(?,?,?,?,?,'staged',?)",
                    (import_id, identity.workspace_id, source_id, job_id, digest, now),
                )
                repository.event(job_id, "queued", {"status": "queued", "revision": 1})
                repository.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)",
                                              (identifier("outbox"), "import.queued", json_text({"job_id": job_id, "workspace_id": identity.workspace_id})))
                return ImportStaged(import_id=import_id, job=dm.JobRef(id=job_id, status="queued"), input_sha256=digest).model_dump(mode="json")
            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route="POST /imports", key=key,
                                        payload={"input_sha256": digest, "filename": filename, "kind": kind, "target_course_id": target_course_id}, operation=operation)
            return ImportStaged.model_validate(result)

    @staticmethod
    def frozen_budgets(row: sqlite3.Row) -> ImportBudgets:
        try:
            return ImportBudgets(**json_object(row["input_json"])["budgets"])
        except (KeyError, TypeError, ValueError):
            raise damaged() from None

    def frozen_store(self, row: sqlite3.Row) -> BlobStore:
        budgets = self.frozen_budgets(row)
        return BlobStore(self.database.settings.data_dir, max_bytes=max(budgets.max_source_bytes, budgets.max_package_bytes))

    @staticmethod
    def _preview_data(row: sqlite3.Row) -> dict[str, Any]:
        return json_object(row["preview_json"]) if row["preview_json"] else {
            "warnings": [], "objects": [], "solutions": [], "bodies": {}, "draft_ids": [], "unresolved_refs": [],
        }

    def _public_preview_data(self, identity: SessionIdentity, row: sqlite3.Row) -> dict[str, Any]:
        if preview_visibility(row) != "learner" and identity.role != "author" and row["status"] in {"failed", "cancelled"}:
            warnings = []
            if row["status"] == "failed":
                result = json_object(row["result_json"]) if row["result_json"] else {}
                code = result.get("error", {}).get("code", "IMPORT_PARSE_FAILED")
                metadata = json_object(row["source_metadata"])
                warnings = metadata.get("safe_failure_diagnostics", []) + [dm.Warning(code=code, message="导入解析失败；原件保留，未确认正式内容。", severity="error").model_dump(mode="json")]
            return {"warnings": warnings, "objects": [], "draft_ids": [], "unresolved_refs": []}
        return self._preview_data(row)

    def preview(self, identity: SessionIdentity, id: str) -> ImportPreview:
        with self._access(identity) as repository:
            row = repository.load(id)
            self._private(identity, row, pending_ok=True)
            data = self._public_preview_data(identity, row)
            courses = [value for value in data["objects"] if value["entity"] == "course"]
            return ImportPreview(id=id, status=row["status"], input_sha256=row["input_sha256"],
                                 warnings=[dm.Warning.model_validate(value) for value in data["warnings"]],
                                 candidate_summary=CandidateSummary(course_title=courses[0]["title"] if courses else "",
                                     lesson_count=sum(value["entity"] == "lesson" for value in data["objects"]),
                                     block_count=sum(value["entity"] == "block" for value in data["objects"]),
                                     unresolved_refs=data.get("unresolved_refs", [])), preview_refs=data["draft_ids"])

    @staticmethod
    def _input_matches(row: sqlite3.Row, digest: str) -> None:
        if row["input_sha256"] != digest:
            raise ApiError(409, "IMPORT_INPUT_CHANGED", "导入原件哈希与确认内容不一致。")

    def _cancel(self, repository: ImportRepository, row: sqlite3.Row) -> None:
        if row["status"] == "committed" or row["job_status"] == "completed":
            raise ApiError(409, "IMPORT_ALREADY_COMMITTED", "已确认的正式内容不能通过取消删除。")
        if row["status"] == "cancelled":
            return
        if row["job_status"] == "failed":
            raise ApiError(409, "JOB_TERMINAL", "失败任务已终止，请重新上传原件。")
        repository.connection.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (row["job_id"],))
        repository.transition(row, job_status="cancelled", import_status="cancelled")
        for draft_id in self._preview_data(row)["draft_ids"]:
            repository.connection.execute("UPDATE drafts SET status='cancelled' WHERE id=? AND workspace_id=?",
                                          (draft_id, repository.workspace_id))

    def cancel(self, identity: SessionIdentity, id: str, request: ImportCancelRequest, key: str | None) -> ImportCancelResponse:
        with self._access(identity) as repository:
            row = repository.load(id)
            self._private(identity, row, pending_ok=True)
            self._input_matches(row, request.expected_input_sha256)
            def operation() -> dict[str, Any]:
                self._cancel(repository, row)
                return ImportCancelResponse(id=id).model_dump(mode="json")
            return ImportCancelResponse.model_validate(execute_idempotent(repository.connection, actor=identity.workspace_id,
                route=f"POST /imports/{id}/cancel", key=key, payload=request.model_dump(mode="json"), operation=operation))

    def cancel_job(self, identity: SessionIdentity, id: str, request: JobCancelRequest, key: str | None) -> JobSnapshot:
        with self._access(identity) as repository:
            row = repository.from_job(id)
            self._private(identity, row, pending_ok=True)
            def operation() -> dict[str, Any]:
                if row["job_revision"] != request.expected_revision:
                    raise ApiError(412, "REVISION_MISMATCH", "任务已改变，请重新读取状态。")
                self._cancel(repository, row)
                return self._job_snapshot(repository, identity, repository.from_job(id)).model_dump(mode="json")
            return JobSnapshot.model_validate(execute_idempotent(repository.connection, actor=identity.workspace_id,
                route=f"POST /jobs/{id}/cancel", key=key, payload=request.model_dump(mode="json"), operation=operation))

    def job(self, identity: SessionIdentity, id: str) -> JobSnapshot:
        with self._access(identity) as repository:
            row = repository.from_job(id)
            self._private(identity, row, pending_ok=True)
            return self._job_snapshot(repository, identity, row)

    def _job_snapshot(self, repository: ImportRepository, identity: SessionIdentity, row: sqlite3.Row) -> JobSnapshot:
        job = repository.connection.execute("SELECT * FROM jobs WHERE id=? AND workspace_id=?", (row["job_id"], identity.workspace_id)).fetchone()
        data = self._public_preview_data(identity, row)
        result = json_object(job["result_json"]) if job["result_json"] else {}
        if preview_visibility(row) != "learner" and identity.role != "author" and row["status"] in {"failed", "cancelled"}:
            result.pop("course_refs", None)
            if result.get("error"):
                result["error"] = dm.ErrorDetail(code=result["error"]["code"], message="导入解析失败；原件保留，未确认正式内容。",
                                                 request_id=result["error"]["request_id"], retryable=False).model_dump(mode="json")
        terminal = job["status"] == "completed"
        return JobSnapshot(id=row["job_id"], workspace_id=identity.workspace_id, kind="import", status=job["status"], revision=job["revision"],
            created_at=job["created_at"], updated_at=job["updated_at"],
            progress=JobProgress(completed=2 if terminal else 1 if row["status"] == "preview_ready" else 0, total=2,
                                 label={"staged": "等待解析", "parsing": "解析原件", "preview_ready": "等待确认预览",
                                        "committed": "导入已确认", "cancelled": "导入已取消", "failed": "解析失败"}[row["status"]]),
            result_refs=[dm.ContentRef.model_validate(value) for value in result.get("course_refs", [])] if terminal else [],
            warnings=[dm.Warning.model_validate(value) for value in data["warnings"]],
            error=dm.ErrorDetail.model_validate(result["error"]) if result.get("error") else None)

    def draft(self, identity: SessionIdentity, id: str) -> ImportDraftSnapshot:
        with self._access(identity) as repository:
            draft = repository.connection.execute("SELECT * FROM drafts WHERE id=? AND workspace_id=?", (id, identity.workspace_id)).fetchone()
            if draft is None:
                raise missing()
            candidate = json_object(draft["candidate_json"])
            row = repository.load(candidate["import_id"])
            self._private(identity, row)
            if id not in self._preview_data(row)["draft_ids"]:
                raise damaged()
            value = ENTITY_MODELS[draft["kind"]].model_validate(candidate["metadata"])
            if metadata_sha256(value) != draft["candidate_sha256"]:
                raise damaged()
            payload: Any = value
            warnings = [dm.Warning.model_validate(warning) for warning in self._preview_data(row)["warnings"]]
            if isinstance(value, dm.ContentBlock):
                info = repository.blob(value.body_sha256)
                body = self.frozen_store(row).read(info.sha256, expected_size=info.size).decode("utf-8")
                metadata = json_object(row["source_metadata"])
                citations = [dm.Citation.model_validate(item) for item in metadata.get("citations", []) if item["id"] in value.citations]
                if {citation.id for citation in citations} != set(value.citations) or len(citations) != len(set(value.citations)):
                    raise damaged()
                locators = {citation.locator for citation in citations}
                warnings = [warning for warning in warnings if warning.locator is None
                            or warning.locator in {f"source:{row['source_id']}", f"source:{row['source_id']};docx:container"}
                            or warning.locator in locators
                            or any(locator.startswith(warning.locator + "/") for locator in locators)]
                payload = BlockDraftPayload(metadata=value, body_markdown=body, source_id=row["source_id"], citations=citations)
            return ImportDraftSnapshot(id=id, kind=value.entity, revision=draft["revision"], base_ref=None,
                state=draft["status"], candidate_sha256=draft["candidate_sha256"], payload=payload,
                warnings=warnings)

    def _artifact(self, repository: ImportRepository, identity: SessionIdentity, id: str) -> tuple[sqlite3.Row, DownloadArtifact]:
        row = repository.connection.execute("SELECT * FROM artifacts WHERE id=? AND workspace_id=?", (id, identity.workspace_id)).fetchone()
        if row is None:
            raise missing()
        if row["visibility"] == "author_private" and identity.role != "author":
            raise ApiError(403, "POLICY_DENIED", "此作者私有附件需要作者角色。")
        metadata = json_object(row["manifest_json"])
        info = repository.blob(row["blob_sha256"])
        if metadata.get("version") != 1 or metadata.get("sha256") != info.sha256 or metadata.get("size") != info.size:
            raise damaged()
        return row, DownloadArtifact(artifact_id=id, filename=metadata["filename"], media_type=metadata["media_type"],
                                      size=info.size, sha256=info.sha256, download_path=f"/api/v1/artifacts/{id}/download")

    def source(self, identity: SessionIdentity, id: str) -> SourceResponse:
        with self._access(identity) as repository:
            row = repository.connection.execute("SELECT * FROM sources WHERE id=? AND workspace_id=?", (id, identity.workspace_id)).fetchone()
            if row is None:
                raise missing()
            metadata = json_object(row["metadata_json"])
            _, artifact = self._artifact(repository, identity, metadata["artifact_id"])
            if row["blob_sha256"] != artifact.sha256:
                raise damaged()
            return SourceResponse(id=id, media_type=row["media_type"], size=artifact.size, sha256=artifact.sha256,
                                  rights=row["rights"], parser_version=row["parser_version"],
                                  warnings=[dm.Warning.model_validate(value) for value in metadata.get("warnings", [])], artifact=artifact)

    def download(self, identity: SessionIdentity, id: str) -> tuple[bytes, DownloadArtifact]:
        with self._access(identity) as repository:
            row, artifact = self._artifact(repository, identity, id)
            imported = repository.from_job(row["job_id"])
            return self.frozen_store(imported).read(artifact.sha256, expected_size=artifact.size), artifact

    def _body_payloads(self, repository: ImportRepository, row: sqlite3.Row, preview: dict[str, Any]) -> dict[str, bytes]:
        output = {}
        for path, digest in preview["bodies"].items():
            info = repository.blob(digest)
            output[path] = self.frozen_store(row).read(info.sha256, expected_size=info.size)
        return output

    def _append_target(self, repository: ImportRepository, row: sqlite3.Row, values: tuple[PublishedModel, ...], bodies: dict[str, bytes]) -> tuple[PublishedModel, ...]:
        raw_ref = json_object(row["input_json"])["target_ref"]
        if raw_ref is None:
            return values
        base = dm.ContentRef.model_validate(raw_ref)
        current = ContentRepository(repository.connection, repository.workspace_id).current(base.id).value
        if not isinstance(current, dm.Course) or reference(current) != base:
            raise ApiError(409, "IMPORT_TARGET_CHANGED", "目标课程已更改，请重新导入并确认新预览。")
        all_courses = [value for value in values if isinstance(value, dm.Course)]
        latest_courses: dict[str, dm.Course] = {}
        for value in all_courses:
            if value.id not in latest_courses or value.revision > latest_courses[value.id].revision:
                latest_courses[value.id] = value
        courses = list(latest_courses.values())
        if not courses:
            raise invalid()
        lesson_refs = list(current.lesson_refs)
        concept_refs = list(current.concept_refs)
        for course in courses:
            for ref in course.lesson_refs:
                if all(existing.id != ref.id for existing in lesson_refs):
                    lesson_refs.append(ref)
                elif ref not in lesson_refs:
                    raise ApiError(409, "IMPORT_ID_COLLISION", "导入小节 ID 与目标课程冲突，请显式映射。")
            for ref in course.concept_refs:
                if all(existing.id != ref.id for existing in concept_refs):
                    concept_refs.append(ref)
                elif ref not in concept_refs:
                    raise ApiError(409, "IMPORT_ID_COLLISION", "导入概念 ID 与目标课程冲突，请显式映射。")
        sections = list(current.sections)
        if sections or any(course.sections for course in courses):
            if not sections:
                sections.append(dm.CourseSection(id=f"section_{row['id'][7:]}_base", title=current.title,
                                                  lesson_ids=[ref.id for ref in current.lesson_refs]))
            for number, course in enumerate(courses):
                groups = course.sections or [dm.CourseSection(id="imported", title=course.title, lesson_ids=[ref.id for ref in course.lesson_refs])]
                for group_number, group in enumerate(groups):
                    sections.append(dm.CourseSection(id=f"section_{row['id'][7:]}_{number}_{group_number}",
                                                     title=group.title, lesson_ids=group.lesson_ids))
        updated = dm.Course.model_validate(current.model_copy(update={"revision": current.revision + 1, "lesson_refs": lesson_refs,
                                                       "concept_refs": concept_refs, "sections": sections}).model_dump(mode="python"))
        rebound, _ = remap_import(values, (), {}, workspace_id=repository.workspace_id, bodies=bodies,
                                  replacements={object_key(course): updated for course in all_courses})
        return tuple(value for value in rebound if not isinstance(value, dm.Course)) + (updated,)

    def commit(self, identity: SessionIdentity, id: str, request: ImportCommitRequest, key: str | None) -> ImportCommitResponse:
        with self._access(identity) as repository:
            row = repository.load(id)
            self._private(identity, row)
            self._input_matches(row, request.expected_input_sha256)
            def operation() -> dict[str, Any]:
                preview = self._preview_data(row)
                request_hash = sha256_bytes(canonical_bytes(request))
                if row["status"] == "committed":
                    if preview.get("commit_request_sha256") == request_hash:
                        return preview["commit_result"]
                    raise ApiError(409, "IMPORT_ALREADY_COMMITTED", "此导入已按其他确认参数提交。")
                if row["status"] != "preview_ready" or row["job_status"] != "awaiting_approval":
                    raise ApiError(409, "IMPORT_NOT_READY", "导入尚未准备好或已经终止。")
                warnings = [dm.Warning.model_validate(value) for value in preview["warnings"]]
                if any(value.severity == "error" for value in warnings):
                    raise ApiError(422, "IMPORT_ERRORS_UNRESOLVED", "预览包含错误，不能确认导入。")
                required = {value.code for value in warnings if value.severity == "warning"}
                acknowledged = set(request.accepted_warning_codes)
                if acknowledged - {value.code for value in warnings}:
                    raise invalid()
                if required - acknowledged:
                    raise ApiError(409, "IMPORT_WARNINGS_UNACKNOWLEDGED", "需要逐项确认预览中的警告。")
                source_info = repository.blob(row["blob_sha256"])
                if source_info.sha256 != row["input_sha256"]:
                    raise damaged()
                self.frozen_store(row).read(source_info.sha256, expected_size=source_info.size)
                preview_registry = {(value["entity"], value["id"], value["revision"]): value for value in preview["objects"]}
                if len(preview_registry) != len(preview["draft_ids"]):
                    raise damaged()
                seen_candidates = set()
                for draft_id in preview["draft_ids"]:
                    draft = repository.connection.execute("SELECT * FROM drafts WHERE id=? AND workspace_id=?", (draft_id, identity.workspace_id)).fetchone()
                    if draft is None or draft["status"] != "draft" or draft["revision"] != 1:
                        raise ApiError(409, "IMPORT_PREVIEW_CHANGED", "导入候选已改变，需要重新生成并确认预览。")
                    candidate = json_object(draft["candidate_json"])
                    value = ENTITY_MODELS[draft["kind"]].model_validate(candidate["metadata"])
                    identity_key = (value.entity, value.id, value.revision)
                    if (candidate.get("import_id") != id or identity_key in seen_candidates
                            or value.model_dump(mode="json") != preview_registry.get(identity_key)
                            or metadata_sha256(value) != draft["candidate_sha256"]):
                        raise damaged()
                    seen_candidates.add(identity_key)
                bodies = self._body_payloads(repository, row, preview)
                originals = tuple(ENTITY_MODELS[value["entity"]].model_validate(value) for value in preview["objects"])
                solutions = tuple(dm.SolutionPrivate.model_validate(value) for value in preview["solutions"])
                mapping = {value.old_id: value.new_id for value in request.id_mapping}
                values, private = remap_import(originals, solutions, mapping, workspace_id=identity.workspace_id, bodies=bodies)
                target = json_object(row["input_json"])["target_ref"]
                for value in values:
                    collision = repository.connection.execute("SELECT 1 FROM objects WHERE id=?", (value.id,)).fetchone()
                    if collision is not None:
                        # Only the explicitly frozen target course receives a new revision.
                        if target is None or not isinstance(value, dm.Course) or value.id != target["id"]:
                            raise ApiError(409, "IMPORT_ID_COLLISION", "导入 ID 已存在，请提供明确的一对一映射。")
                imported_course_ids = {value.id for value in values if isinstance(value, dm.Course)}
                values = self._append_target(repository, row, values, bodies)
                refs = self.content.publish_in_transaction(repository.connection, identity.workspace_id, values, bodies, import_history=True, budgets=self.frozen_budgets(row))
                for solution in private:
                    if solution.question_ref.entity != "question":
                        raise invalid()
                    repository.connection.execute(
                        "INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) VALUES(?,?,?,?,?,'needs_review')",
                        (solution.question_ref.id, solution.question_ref.revision, solution.revision,
                         json_text(solution), metadata_sha256(solution)),
                    )
                course_refs = [ref for ref in refs if ref.entity == "course"]
                source_metadata = json_object(row["source_metadata"])
                remapped_lookup = {(value.entity, value.id, value.revision): value for value in values}
                original_symbols = source_metadata.get("symbols", [])
                mapped_symbols = []
                for raw_symbol in original_symbols:
                    symbol = dm.Symbol.model_validate(raw_symbol)
                    old_ref = symbol.first_definition
                    target_value = remapped_lookup.get((old_ref.entity, mapping.get(old_ref.id, old_ref.id), old_ref.revision))
                    if target_value is None:
                        raise invalid()
                    scope = mapping.get(symbol.scope, symbol.scope)
                    if target is not None and scope in imported_course_ids:
                        scope = target["id"]
                    mapped_symbols.append(symbol.model_copy(update={"scope": scope,
                                                                   "first_definition": reference(target_value)}).model_dump(mode="json"))
                source_metadata["original_symbols"] = original_symbols
                source_metadata["symbols"] = mapped_symbols
                repository.connection.execute("UPDATE sources SET metadata_json=? WHERE id=? AND workspace_id=?",
                                              (json_text(source_metadata), row["source_id"], identity.workspace_id))
                ProvenanceRepository(repository.connection, identity.workspace_id).freeze_import(id, values)
                receipt = {"schema_version": "3.0.0", "kind": "import_migration_receipt", "input_sha256": row["input_sha256"],
                           "source_id": row["source_id"], "parser_version": preview["parser_version"], "id_mapping": mapping,
                           "commit_request": request.model_dump(mode="json"),
                           "target_base_ref": target, "budgets": asdict(self.frozen_budgets(row)),
                           "workspace_remapped_note_ids": [value.id for value in values if isinstance(value, dm.Note)],
                           "course_refs": [value.model_dump(mode="json") for value in course_refs],
                           "accepted_warning_codes": sorted(acknowledged), "mathematical": "NOT_RUN", "sources": "NOT_RUN",
                           "private_solution_count": len(private), "solution_review_status": "needs_review", "created_at": utc_now()}
                info = self.frozen_store(row).write(canonical_bytes(receipt))
                receipt_id = repository.artifact(info=info, filename="import-receipt.json", media_type="application/json",
                                                 visibility=preview_visibility(row), profile="import_receipt", job_id=row["job_id"])
                result = ImportCommitResponse(course_refs=course_refs, migration_receipt_id=receipt_id).model_dump(mode="json")
                preview["commit_request_sha256"] = request_hash
                preview["commit_result"] = result
                repository.connection.execute("UPDATE ingestion_imports SET preview_json=? WHERE id=?", (json_text(preview), id))
                for draft_id in preview["draft_ids"]:
                    repository.connection.execute("UPDATE drafts SET status='published' WHERE id=? AND workspace_id=?", (draft_id, identity.workspace_id))
                repository.transition(row, job_status="completed", import_status="committed", result=result)
                return result
            try:
                result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=f"POST /imports/{id}/commit", key=key,
                                            payload=request.model_dump(mode="json"), operation=operation)
                return ImportCommitResponse.model_validate(result)
            except (ValueError, TypeError, KeyError, ValidationError):
                raise invalid() from None
