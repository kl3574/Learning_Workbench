"""Explicit local retrieval, durable rebuild commands and atomic generations."""

import base64
from collections.abc import Callable
import hashlib
import hmac
import re
import secrets
import sqlite3
from uuid import uuid4

from pydantic import TypeAdapter
from starlette.responses import JSONResponse

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json

from ..import_dto import JobCancelRequest, JobProgress, JobSnapshot
from ..infrastructure.database import Database, utc_now
from ..infrastructure.retrieval_job_repository import RetrievalJobRepository, RetrievalLease
from ..infrastructure.retrieval_repository import RetrievalInvalidation, RetrievalRepository, index_integrity
from ..infrastructure.security import SessionIdentity, expires_after
from ..retrieval_dto import (
    RetrievalCommittedIndex, RetrievalHitView, RetrievalIndexOverview, RetrievalIndexRebuildWrite,
    RetrievalIndexScopeStatus, RetrievalJobError, RetrievalJobSummary, RetrievalOmissionCounts,
    RetrievalQueryView, RetrievalQueryWrite, RetrievalRegisteredScope, RetrievalWholeBlockLocation,
    RetrievalIndexState, RetrievalResultState, ref_sort_key,
)
from .content_retrieval import ContentRetrievalSource
from .errors import ApiError
from .policy import Policy
from .retrieval_lexical import coverage_score, terms_sha256, tokenize, tokenize_query
from .retrieval_models import RetrievalIndexedBlock, RetrievalIndexManifest, RetrievalScopeSnapshot

TEXT_BUDGET = 2 * 1024 * 1024
JSON_BUDGET = 8 * 1024 * 1024


def warning(code: str, message: str) -> dm.Warning:
    return dm.Warning(code=code, message=message, locator=None, severity='warning')


def json_bytes(view: RetrievalQueryView) -> bytes:
    # Match the actual response encoder, including JSON escaping and UTF-8.
    return bytes(JSONResponse(view.model_dump(mode='json')).body)


def job_error(row: sqlite3.Row) -> dm.ErrorDetail | None:
    if row['status'] != 'failed':
        return None
    try:
        parsed = strict_json(row['result_json'])
        if not isinstance(parsed, dict) or set(parsed) != {'error'}:
            raise index_integrity()
        return dm.ErrorDetail.model_validate(parsed['error'])
    except (TypeError, ValueError, KeyError):
        raise index_integrity() from None


def job_summary(latest) -> RetrievalJobSummary | None:
    if latest is None:
        return None
    row, value, _ = latest
    error = job_error(row)
    return RetrievalJobSummary(job=dm.JobRef(id=row['id'], status=row['status']),
        target_corpus_sha256=value.expected_corpus_sha256,
        error=RetrievalJobError(code=error.code, message=error.message, retryable=error.retryable) if error else None)


class RetrievalService:
    def __init__(self, database: Database):
        self.database = database
        self.source = ContentRetrievalSource(database)
        self._cursor_key = secrets.token_bytes(32)

    def _status(self, connection: sqlite3.Connection, snapshot: RetrievalScopeSnapshot):
        repo = RetrievalRepository(connection, snapshot.descriptor.workspace_id)
        digest = snapshot.descriptor.scope_sha256
        scope = repo.scope(digest)
        generation = repo.generation(scope)
        latest = repo.latest_job(digest)
        manifest = generation[0] if generation else None
        state: RetrievalIndexState
        if manifest is not None and manifest.corpus_sha256 == snapshot.corpus_sha256:
            state = 'ready'
        elif (latest is not None and latest[0]['status'] in {'queued', 'running', 'awaiting_approval'}
              and latest[1].expected_corpus_sha256 == snapshot.corpus_sha256):
            state = 'building'
        elif manifest is not None:
            state = 'stale'
        else:
            state = 'missing'
        status = RetrievalIndexScopeStatus(kind='scope', scope_sha256=digest, scope_refs=snapshot.descriptor.scope_refs,
            corpus_sha256=snapshot.corpus_sha256, state=state,
            indexed_corpus_sha256=manifest.corpus_sha256 if manifest else None,
            index_version=manifest.index_version if manifest else None, last_built_at=manifest.built_at if manifest else None,
            latest_job=job_summary(latest))
        return status, generation

    def scope_status(self, identity: SessionIdentity, scope_refs: list[dm.ContentRef]) -> RetrievalIndexScopeStatus:
        with self.database.transaction(immediate=False) as connection:
            snapshot = self.source.resolve_scope(connection, identity, scope_refs)
            return self._status(connection, snapshot)[0]

    def _after(self, identity: SessionIdentity, cursor: str | None, limit: int) -> str:
        if cursor is None:
            return ''
        try:
            if not 1 <= len(cursor) <= 1024 or re.fullmatch(r'[A-Za-z0-9_-]+', cursor) is None:
                raise ValueError('invalid cursor')
            raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                raise ValueError('invalid cursor')
            data = strict_json(raw[32:])
            if (not isinstance(data, dict) or set(data) != {'workspace_id', 'limit', 'after', 'expires_at'}
                    or data['workspace_id'] != identity.workspace_id or type(data['limit']) is not int or data['limit'] != limit):
                raise ValueError('invalid cursor context')
            TypeAdapter(dm.Sha256).validate_python(data['after'])
            TypeAdapter(dm.UTC).validate_python(data['expires_at'])
            if data['expires_at'] <= utc_now():
                raise ApiError(409, 'CURSOR_EXPIRED', '索引分页游标已过期，请从第一页重新读取。')
            return data['after']
        except (ValueError, TypeError, KeyError):
            raise ApiError(422, 'CURSOR_INVALID', '索引分页游标无效，请从第一页重新读取。') from None

    def _cursor(self, identity: SessionIdentity, limit: int, after: str) -> str:
        raw = canonical_bytes({'workspace_id': identity.workspace_id, 'limit': limit,
                               'after': after, 'expires_at': expires_after(900)})
        return base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')

    def overview(self, identity: SessionIdentity, *, cursor: str | None = None, limit: int = 20) -> RetrievalIndexOverview:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(422, 'SCHEMA_INVALID', '分页数量须为1至100的整数。')
        with self.database.transaction(immediate=False) as connection:
            Policy(connection, identity.workspace_id).check('subject_read')
            after = self._after(identity, cursor, limit)
            repo = RetrievalRepository(connection, identity.workspace_id)
            rows = repo.scopes(after, limit + 1)
            items = []
            for row in rows[:limit]:
                generation = repo.generation(row)
                manifest = generation[0] if generation else None
                items.append(RetrievalRegisteredScope(scope_sha256=row['scope_sha256'], scope_refs=repo.roots(row),
                    latest_index=RetrievalCommittedIndex(index_version=manifest.index_version,
                        corpus_sha256=manifest.corpus_sha256, built_at=manifest.built_at, block_count=len(manifest.blocks),
                        term_count=sum(block.term_count for block in manifest.blocks)) if manifest else None,
                    latest_job=job_summary(repo.latest_job(row['scope_sha256']))))
            return RetrievalIndexOverview(kind='overview', items=items,
                next_cursor=self._cursor(identity, limit, rows[limit - 1]['scope_sha256']) if len(rows) > limit else None)

    def rebuild(self, identity: SessionIdentity, request: RetrievalIndexRebuildWrite, key: str) -> dm.JobRef:
        with self.database.transaction() as connection:
            Policy(connection, identity.workspace_id).check('subject_read')
            repo = RetrievalRepository(connection, identity.workspace_id)
            previous = repo.replay('POST /index/rebuild', key, request, dm.JobRef)
            if previous is not None:
                return previous
            if request.provider_id is not None or request.consent_id is not None:
                raise ApiError(409, 'CAPABILITY_UNSUPPORTED', '本地索引不使用模型、外部分词或联网授权。')
            snapshot = self.source.resolve_scope(connection, identity, request.scope_refs)
            if request.expected_corpus_sha256 != snapshot.corpus_sha256:
                raise ApiError(412, 'INDEX_CORPUS_CONFLICT', '检索范围的实际材料描述已改变，请重新读取后明确重建。')
            ack = repo.enqueue(snapshot, request)
            repo.record_command('POST /index/rebuild', key, request, ack, ack.id)
            return ack

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as connection:
            Policy(connection, identity.workspace_id).check('subject_read')
            repo = RetrievalRepository(connection, identity.workspace_id)
            return self._job_snapshot(repo, identifier)

    @staticmethod
    def _job_snapshot(repo: RetrievalRepository, identifier: str) -> JobSnapshot:
        row, value, result = repo.job(identifier)
        refs = []
        if result is not None:
            manifest, _ = repo.generation_by_id(result.index_version, value.scope_sha256)
            refs = [block.ref for block in manifest.blocks]
        return JobSnapshot(id=identifier, workspace_id=repo.workspace_id, kind='retrieval_index', status=row['status'],
            revision=row['revision'], created_at=row['created_at'], updated_at=row['updated_at'],
            progress=JobProgress(completed=len(refs), total=len(value.descriptor.blocks), label={
                'queued': '等待构建索引', 'running': '正在核验材料并构建索引', 'completed': '索引构建完成',
                'failed': '索引构建失败，既有代际保留', 'cancelled': '索引构建已取消，既有代际保留',
            }[row['status']]), result_refs=refs, warnings=[], error=job_error(row))

    def cancel_job(self, identity: SessionIdentity, identifier: str, request: JobCancelRequest, key: str) -> JobSnapshot:
        with self.database.transaction() as connection:
            Policy(connection, identity.workspace_id).check('subject_read')
            repo = RetrievalRepository(connection, identity.workspace_id)
            route = f'POST /jobs/{identifier}/cancel'
            previous = repo.replay(route, key, request, JobSnapshot)
            if previous is not None:
                return previous
            row, _, _ = repo.job(identifier)
            if row['revision'] != request.expected_revision:
                raise ApiError(412, 'JOB_REVISION_CONFLICT', '任务状态已改变，请重新读取后确认取消。')
            repo.jobs.terminal(row, 'cancelled')
            ack = self._job_snapshot(repo, identifier)
            repo.record_command(route, key, request, ack, identifier)
            return ack

    @staticmethod
    def _view(status: RetrievalIndexScopeStatus, *, matched_count: int | None, hits: list[RetrievalHitView],
              omissions: RetrievalOmissionCounts, empty_index: bool = False) -> RetrievalQueryView:
        warnings = []
        result_state: RetrievalResultState
        if status.state != 'ready':
            result_state = 'not_ready'
            warnings.append(warning(f'INDEX_{status.state.upper()}', {
                'missing': '所选范围尚未建立索引。', 'building': '所选范围的索引任务尚未完成。',
                'stale': '材料描述已变化，需要明确重建索引。',
            }[status.state]))
        elif hits:
            result_state = 'matched'
        elif matched_count:
            result_state = 'resource_omitted'
        else:
            result_state = 'indexed_empty' if empty_index else 'no_match'
        if omissions.text_byte_budget or omissions.json_byte_budget:
            warnings.append(warning('RETRIEVAL_RESOURCE_OMITTED', '部分匹配的完整材料超过返回资源预算，未截断正文或来源。'))
        return RetrievalQueryView(scope_sha256=status.scope_sha256, scope_refs=status.scope_refs,
            corpus_sha256=status.corpus_sha256, indexed_corpus_sha256=status.indexed_corpus_sha256,
            index_version=status.index_version, index_state=status.state, result_state=result_state,
            matched_count=matched_count, hits=hits, omissions=omissions, warnings=warnings)

    def query(self, identity: SessionIdentity, request: RetrievalQueryWrite) -> RetrievalQueryView:
        with self.database.transaction(immediate=False) as connection:
            Policy(connection, identity.workspace_id).check('subject_read')
            query_terms = tokenize_query(request.query)
            snapshot = self.source.resolve_scope(connection, identity, request.scope_refs)
            status, generation = self._status(connection, snapshot)
            if status.state != 'ready':
                return self._view(status, matched_count=None, hits=[],
                    omissions=RetrievalOmissionCounts(result_limit=0, text_byte_budget=0, json_byte_budget=0))
            if generation is None:
                raise index_integrity()
            manifest, terms = generation
            repo = RetrievalRepository(connection, identity.workspace_id)
            matches = repo.match(manifest, query_terms, terms)
            ranked = sorted((block for block in manifest.blocks if block.chunk_id in matches),
                key=lambda block: (-coverage_score(query_terms, terms[block.chunk_id]), ref_sort_key(block.ref)))
        matched = len(ranked)
        hit_descriptors = {ref_sort_key(block.ref): block for block in snapshot.descriptor.blocks}
        states = {ref_sort_key(item.ref): item for item in snapshot.descriptor.graph}
        hits: list[RetrievalHitView] = []
        omitted = {'result_limit': 0, 'text_byte_budget': 0, 'json_byte_budget': 0}
        text_size = 0
        for position, block in enumerate(ranked):
            if len(hits) >= request.limit:
                omitted['result_limit'] += 1
                continue
            if text_size + block.body_bytes > TEXT_BUDGET:
                omitted['text_byte_budget'] += 1
                continue
            with self.database.transaction(immediate=False) as connection:
                material = self.source.read_material(connection, identity, snapshot, block.ref)
            text = material.body.decode('utf-8', errors='strict')
            if (material.body_sha256 != block.body_sha256 or len(material.body) != block.body_bytes
                    or len(text) != block.body_codepoints or terms_sha256(tokenize(text)) != block.terms_sha256):
                raise index_integrity()
            descriptor, current = hit_descriptors[ref_sort_key(block.ref)], states[ref_sort_key(block.ref)]
            warnings = [warning('MATERIAL_UNREVIEWED', '来自所选未审材料，不代表内容已核验。')]
            if current.current_ref != block.ref:
                warnings.append(warning('HISTORICAL_REVISION', '这是明确选定的历史修订，未自动改为当前版本。'))
            if current.lifecycle == 'archived':
                warnings.append(warning('CONTENT_ARCHIVED', '该材料已归档；此处保留明确选定修订的只读内容。'))
            hit = RetrievalHitView(ref=block.ref, title=descriptor.title, text=text,
                locator=f'block:{block.ref.id}@r{block.ref.revision};body:{block.body_sha256};cp:0-{len(text)}',
                score=coverage_score(query_terms, terms[block.chunk_id]), body_sha256=block.body_sha256,
                location=RetrievalWholeBlockLocation(version='whole-block-v1', unit='unicode_codepoint', start_cp=0, end_cp=len(text)),
                current_ref=current.current_ref, lifecycle=current.lifecycle, material_review='unreviewed',
                provenance=descriptor.provenance, parent_paths=descriptor.parent_paths, warnings=warnings)
            # Account for not-yet-considered matches only in this sizing view.
            tentative = RetrievalOmissionCounts(**{**omitted, 'result_limit': omitted['result_limit'] + matched - position - 1})
            if len(json_bytes(self._view(status, matched_count=matched, hits=[*hits, hit], omissions=tentative))) > JSON_BUDGET:
                omitted['json_byte_budget'] += 1
            else:
                hits.append(hit)
                text_size += block.body_bytes
        empty = sum(block.term_count for block in manifest.blocks) == 0
        view = self._view(status, matched_count=matched, hits=hits, omissions=RetrievalOmissionCounts(**omitted), empty_index=empty)
        while len(json_bytes(view)) > JSON_BUDGET and hits:
            hits.pop()
            omitted['json_byte_budget'] += 1
            view = self._view(status, matched_count=matched, hits=hits, omissions=RetrievalOmissionCounts(**omitted), empty_index=empty)
        if len(json_bytes(view)) > JSON_BUDGET:
            raise ApiError(413, 'RETRIEVAL_RESPONSE_BUDGET_EXCEEDED', '完整检索诊断超过返回资源预算。')
        with self.database.transaction(immediate=False) as connection:
            self.source.revalidate_scope(connection, identity, snapshot)
            # Recheck the selected complete generation, not a guessed current row.
            RetrievalRepository(connection, identity.workspace_id).generation_by_id(manifest.index_version, manifest.scope_sha256)
        return view


class RetrievalStopped(Exception):
    pass


class RetrievalWorker:
    def __init__(self, database: Database, *, stopping: Callable[[], bool] | None = None):
        self.database = database
        self.source = ContentRetrievalSource(database)
        self.stopping = stopping or (lambda: False)
        self.lease_seconds = 90

    @staticmethod
    def _identity(workspace_id: str) -> SessionIdentity:
        # Trusted local worker identity derived from a Jobs-owned lease. Never
        # accepts browser role claims or confers access to private answer stores.
        return SessionIdentity('retrieval_worker', workspace_id, 'learner', '', expires_after(86400))

    def claim(self) -> RetrievalLease | None:
        if self.stopping():
            return None
        workspace_id = self.database.workspace_id()
        with self.database.transaction() as connection:
            Policy(connection, workspace_id).check('subject_read')
            jobs = RetrievalJobRepository(connection, workspace_id)
            available = jobs.available()
            if available is None:
                return None
            row, _, _ = RetrievalRepository(connection, workspace_id).job(available['id'])
            return jobs.claim(row, self.lease_seconds)

    def compute(self, lease: RetrievalLease) -> tuple[RetrievalIndexManifest, dict[str, tuple[str, ...]]]:
        identity = self._identity(lease.workspace_id)
        with self.database.transaction(immediate=False) as connection:
            repo = RetrievalRepository(connection, lease.workspace_id)
            row, value, _ = repo.job(lease.job_id)
            if not repo.jobs.owned(row, lease):
                raise RetrievalStopped()
            snapshot = RetrievalScopeSnapshot(descriptor=value.descriptor, corpus_sha256=value.expected_corpus_sha256)
            self.source.revalidate_scope(connection, identity, snapshot)
        indexed, tokens = [], {}
        for descriptor in snapshot.descriptor.blocks:
            if self.stopping():
                raise RetrievalStopped()
            with self.database.transaction() as connection:
                repo = RetrievalRepository(connection, lease.workspace_id)
                row, _, _ = repo.job(lease.job_id)
                Policy(connection, lease.workspace_id).check('subject_read')
                if not repo.jobs.renew(row, lease, self.lease_seconds):
                    raise RetrievalStopped()
            # Actual body read uses only a read transaction. Tokenization and all
            # complete-block derivation happen outside any database transaction.
            with self.database.transaction(immediate=False) as connection:
                material = self.source.read_material(connection, identity, snapshot, descriptor.ref)
            text = material.body.decode('utf-8', errors='strict')
            terms = tokenize(text)
            chunk_id = f'chunk_{uuid4().hex}'
            indexed.append(RetrievalIndexedBlock(ref=descriptor.ref, body_sha256=material.body_sha256,
                body_bytes=len(material.body), body_codepoints=len(text), chunk_id=chunk_id,
                terms_sha256=terms_sha256(terms), term_count=len(terms)))
            tokens[chunk_id] = terms
        return RetrievalIndexManifest(version='retrieval-index-v1', index_version=f'index_{uuid4().hex}',
            scope_sha256=snapshot.descriptor.scope_sha256, corpus_sha256=snapshot.corpus_sha256,
            descriptor=snapshot.descriptor, built_at=utc_now(), blocks=indexed), tokens

    def finish(self, lease: RetrievalLease, manifest: RetrievalIndexManifest, terms: dict[str, tuple[str, ...]]) -> bool:
        if self.stopping():
            return False
        with self.database.transaction() as connection:
            repo = RetrievalRepository(connection, lease.workspace_id)
            row, value, _ = repo.job(lease.job_id)
            if not repo.jobs.owned(row, lease):
                return False
            self.source.revalidate_scope(connection, self._identity(lease.workspace_id),
                RetrievalScopeSnapshot(descriptor=value.descriptor, corpus_sha256=value.expected_corpus_sha256))
            result = repo.publish(lease.job_id, manifest, terms)
            repo.jobs.terminal(row, 'completed', result.model_dump(mode='json'))
            repo.generation_by_id(manifest.index_version, manifest.scope_sha256)
            return True

    def fail(self, lease: RetrievalLease, error: ApiError) -> None:
        with self.database.transaction() as connection:
            repo = RetrievalRepository(connection, lease.workspace_id)
            row, _, _ = repo.job(lease.job_id)
            if repo.jobs.owned(row, lease):
                detail = dm.ErrorDetail(code=error.code, message='索引构建未完成；原材料及既有索引代际保留。',
                    request_id=f'request_{uuid4().hex}', retryable=error.retryable)
                repo.jobs.terminal(row, 'failed', {'error': detail.model_dump(mode='json')})

    def run_once(self) -> bool:
        lease = None
        try:
            if self.stopping():
                return False
            with self.database.transaction() as connection:
                consumed = RetrievalInvalidation(connection, self.database.workspace_id()).consume_one()
            lease = self.claim()
            if lease is None:
                return consumed
            manifest, terms = self.compute(lease)
            self.finish(lease, manifest, terms)
            return True
        except RetrievalStopped:
            return lease is not None
        except ApiError as error:
            if lease is not None:
                self.fail(lease, error)
                return True
            if error.code == 'ASSESSMENT_ACTIVE':
                return False
            raise
