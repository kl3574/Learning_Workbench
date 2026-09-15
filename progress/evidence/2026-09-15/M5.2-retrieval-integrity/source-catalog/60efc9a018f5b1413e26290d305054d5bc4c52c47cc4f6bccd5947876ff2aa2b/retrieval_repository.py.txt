"""Retrieval-owned immutable scope, command and complete-generation ledgers.

Public Content and Jobs are accessed through their owners. The local FTS table
contains only verified derived tokens, never private originals or body copies.
"""

import re
import sqlite3
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..application.retrieval_lexical import terms_sha256
from ..application.retrieval_models import (
    RetrievalIndexJobInput, RetrievalIndexJobResult, RetrievalIndexManifest,
    RetrievalScopeSnapshot, SCOPE_BYTE_BUDGET, scope_sha256,
)
from ..retrieval_dto import RetrievalIndexRebuildWrite, RetrievalScopeRefs
from ..import_dto import JobCancelRequest, JobSnapshot, JobProgress
from .database import utc_now
from .retrieval_job_repository import RetrievalJobRepository

M = TypeVar('M', bound=BaseModel)


def index_integrity() -> ApiError:
    return ApiError(409, 'INDEX_INTEGRITY_INVALID', '索引范围、清单、来源绑定或词法数据未通过完整性校验。')


def checked_json(model: type[M], raw: str, digest: str | None = None) -> M:
    try:
        if len(raw.encode()) > SCOPE_BYTE_BUDGET + 1024 * 1024:
            raise index_integrity()
        value = model.model_validate(strict_json(raw))
        if canonical_bytes(value).decode() != raw or digest is not None and sha256_bytes(raw.encode()) != digest:
            raise index_integrity()
        return value
    except (ValueError, TypeError, KeyError):
        raise index_integrity() from None


class RetrievalInvalidation:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def changed(self, source: str) -> None:
        if not self.connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '索引输入变化须在来源动作的同一事务登记。')
        if not re.fullmatch(r'[a-z][a-z0-9_.]{0,99}', source):
            raise ValueError('bounded safe event name required')
        present = self.connection.execute("SELECT 1 FROM sqlite_master WHERE name='retrieval_input_events' AND type='table'").fetchone()
        if present is None:
            versions = [row[0] for row in self.connection.execute('SELECT version FROM schema_migrations')]
            if versions and all(version[:4].isdigit() and int(version[:4]) < 11 for version in versions):
                return
            raise index_integrity()
        self.connection.execute('INSERT INTO retrieval_input_events(workspace_id,source,occurred_at) VALUES(?,?,?)',
                                (self.workspace_id, source, utc_now()))

    def consume_one(self) -> bool:
        """Own watermark only; shared Content/Learning outbox is never consumed."""
        row = self.connection.execute('SELECT last_sequence FROM retrieval_consumption WHERE workspace_id=?',
                                      (self.workspace_id,)).fetchone()
        after = row[0] if row else 0
        event = self.connection.execute('SELECT sequence FROM retrieval_input_events WHERE workspace_id=? AND sequence>? '
                                        'ORDER BY sequence LIMIT 1', (self.workspace_id, after)).fetchone()
        if event is None:
            return False
        self.connection.execute('INSERT INTO retrieval_consumption(workspace_id,last_sequence) VALUES(?,?) '
            'ON CONFLICT(workspace_id) DO UPDATE SET last_sequence=excluded.last_sequence', (self.workspace_id, event[0]))
        return True


class RetrievalRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.jobs = RetrievalJobRepository(connection, workspace_id)

    def scope(self, digest: str) -> sqlite3.Row | None:
        row = self.connection.execute('SELECT * FROM retrieval_scopes WHERE workspace_id=? AND scope_sha256=?',
                                      (self.workspace_id, digest)).fetchone()
        if row is not None:
            self.roots(row)
        return row

    def roots(self, row: sqlite3.Row) -> list[dm.ContentRef]:
        try:
            roots = TypeAdapter(RetrievalScopeRefs).validate_python(strict_json(row['roots_json']))
            if (row['workspace_id'] != self.workspace_id or scope_sha256(self.workspace_id, roots) != row['scope_sha256']
                    or canonical_bytes([ref.model_dump(mode='json') for ref in roots]).decode() != row['roots_json']):
                raise index_integrity()
            TypeAdapter(dm.UTC).validate_python(row['created_at'])
            return roots
        except (ValueError, TypeError, KeyError):
            raise index_integrity() from None

    def scopes(self, after: str, limit: int) -> list[sqlite3.Row]:
        rows = self.connection.execute('SELECT * FROM retrieval_scopes WHERE workspace_id=? AND scope_sha256>? '
            'ORDER BY scope_sha256 LIMIT ?', (self.workspace_id, after, limit)).fetchall()
        for row in rows:
            self.roots(row)
        return rows

    def replay(self, route: str, key: str, request: BaseModel, ack_model: type[M]) -> M | None:
        if re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key) is None:
            raise ApiError(400, 'IDEMPOTENCY_KEY_REQUIRED', '此操作需要单个有效的原命令幂等键。')
        row = self.connection.execute('SELECT * FROM retrieval_commands WHERE workspace_id=? AND route=? AND key=?',
                                      (self.workspace_id, route, key)).fetchone()
        if row is None:
            return None
        raw = canonical_bytes(request).decode()
        if sha256_bytes(row['request_json'].encode()) != row['request_sha256']:
            raise index_integrity()
        if raw != row['request_json']:
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '相同幂等键不能用于不同请求。')
        ack = checked_json(ack_model, row['ack_json'], row['ack_sha256'])
        if getattr(ack, 'id', None) != row['job_id']:
            raise index_integrity()
        job, value, _ = self.job(row['job_id'])
        if row['scope_sha256'] != value.scope_sha256:
            raise index_integrity()
        if isinstance(request, RetrievalIndexRebuildWrite):
            if value.request_sha256 != row['request_sha256'] or job['id'] != getattr(ack, 'id', None):
                raise index_integrity()
        elif isinstance(request, JobCancelRequest):
            expected = JobSnapshot(id=job['id'], workspace_id=self.workspace_id, kind='retrieval_index',
                status='cancelled', revision=request.expected_revision + 1, created_at=job['created_at'],
                updated_at=job['updated_at'], progress=JobProgress(completed=0, total=len(value.descriptor.blocks),
                    label='索引构建已取消，既有代际保留'), result_refs=[], warnings=[], error=None)
            if (route != f"POST /jobs/{job['id']}/cancel" or job['status'] != 'cancelled'
                    or job['revision'] != expected.revision or ack != expected):
                raise index_integrity()
        return ack

    def record_command(self, route: str, key: str, request: BaseModel, ack: BaseModel, job_id: str) -> None:
        raw, result = canonical_bytes(request), canonical_bytes(ack)
        allocation = self.connection.execute('SELECT scope_sha256 FROM retrieval_jobs WHERE job_id=? AND workspace_id=?',
                                             (job_id, self.workspace_id)).fetchone()
        if allocation is None:
            raise index_integrity()
        self.connection.execute('INSERT INTO retrieval_commands VALUES(?,?,?,?,?,?,?,?,?,?)',
            (self.workspace_id, route, key, raw.decode(), sha256_bytes(raw), result.decode(), sha256_bytes(result),
             job_id, utc_now(), allocation['scope_sha256']))

    def latest_job(self, digest: str) -> tuple[sqlite3.Row, RetrievalIndexJobInput, RetrievalIndexJobResult | None] | None:
        rows = self.connection.execute('SELECT job_id,sequence FROM retrieval_jobs WHERE workspace_id=? AND scope_sha256=? '
            'ORDER BY sequence', (self.workspace_id, digest)).fetchall()
        commands = self.connection.execute("SELECT job_id FROM retrieval_commands WHERE workspace_id=? AND scope_sha256=? "
            "AND route='POST /index/rebuild'", (self.workspace_id, digest)).fetchall()
        if (len(commands) != len(rows) or {row['job_id'] for row in rows} != {row['job_id'] for row in commands}
                or [row['sequence'] for row in rows] != list(range(1, len(rows) + 1))):
            raise index_integrity()
        values = [self.job(row['job_id']) for row in rows]
        active = [index for index, value in enumerate(values) if value[0]['status'] not in {'completed', 'failed', 'cancelled'}]
        if len(active) > 1 or active and active[0] != len(values) - 1:
            raise index_integrity()
        generations = self.connection.execute('SELECT index_version,job_id,corpus_sha256,manifest_sha256,built_at '
            'FROM retrieval_generations WHERE workspace_id=? AND scope_sha256=?', (self.workspace_id, digest)).fetchall()
        completed = {value[0]['id']: value[2] for value in values if value[0]['status'] == 'completed'}
        if len(generations) != len(completed) or {row['job_id'] for row in generations} != set(completed):
            raise index_integrity()
        for generation in generations:
            result = completed[generation['job_id']]
            if (result is None or result.index_version != generation['index_version']
                    or result.corpus_sha256 != generation['corpus_sha256']
                    or result.manifest_sha256 != generation['manifest_sha256'] or result.built_at != generation['built_at']):
                raise index_integrity()
        if not values and self.scope(digest) is not None:
            raise index_integrity()
        return values[-1] if values else None

    def job(self, identifier: str) -> tuple[sqlite3.Row, RetrievalIndexJobInput, RetrievalIndexJobResult | None]:
        row = self.jobs.load(identifier)
        own = self.connection.execute('SELECT * FROM retrieval_jobs WHERE job_id=? AND workspace_id=?',
                                      (identifier, self.workspace_id)).fetchone()
        if own is None:
            raise index_integrity()
        value = checked_json(RetrievalIndexJobInput, own['input_json'], own['input_sha256'])
        if (value.workspace_id != self.workspace_id or value.scope_sha256 != own['scope_sha256']
                or own['input_json'] != row['input_json'] or own['input_sha256'] != row['input_sha256']):
            raise index_integrity()
        original_request = RetrievalIndexRebuildWrite(scope_refs=value.descriptor.scope_refs,
            expected_corpus_sha256=value.expected_corpus_sha256, provider_id=None, consent_id=None)
        request_raw = canonical_bytes(original_request)
        if value.request_sha256 != sha256_bytes(request_raw):
            raise index_integrity()
        commands = self.connection.execute("SELECT * FROM retrieval_commands WHERE workspace_id=? AND job_id=? "
            "AND route='POST /index/rebuild'", (self.workspace_id, identifier)).fetchall()
        if len(commands) != 1:
            raise index_integrity()
        command = commands[0]
        ack = checked_json(dm.JobRef, command['ack_json'], command['ack_sha256'])
        if (command['request_json'] != request_raw.decode() or command['request_sha256'] != value.request_sha256
                or command['scope_sha256'] != value.scope_sha256
                or ack != dm.JobRef(id=identifier, status='queued')
                or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', command['key']) is None):
            raise index_integrity()
        scope = self.scope(value.scope_sha256)
        if scope is None or self.roots(scope) != value.descriptor.scope_refs:
            raise index_integrity()
        result = None
        if row['status'] == 'completed':
            if own['result_json'] is None:
                raise index_integrity()
            result = checked_json(RetrievalIndexJobResult, own['result_json'], own['result_sha256'])
            if (row['result_json'] != own['result_json'] or result.scope_sha256 != value.scope_sha256
                    or result.corpus_sha256 != value.expected_corpus_sha256):
                raise index_integrity()
        elif own['result_json'] is not None:
            raise index_integrity()
        return row, value, result

    def enqueue(self, snapshot: RetrievalScopeSnapshot, request: RetrievalIndexRebuildWrite) -> dm.JobRef:
        digest = snapshot.descriptor.scope_sha256
        latest = self.latest_job(digest)
        if latest is not None and latest[0]['status'] not in {'completed', 'failed', 'cancelled'}:
            raise ApiError(409, 'INDEX_REBUILD_ACTIVE', '此范围已有未结束的索引任务。')
        value = RetrievalIndexJobInput(version='retrieval-index-job-v1', workspace_id=self.workspace_id,
            request_sha256=sha256_bytes(canonical_bytes(request)), scope_sha256=digest,
            expected_corpus_sha256=snapshot.corpus_sha256, descriptor=snapshot.descriptor)
        self.connection.execute('INSERT OR IGNORE INTO retrieval_scopes VALUES(?,?,?,?,NULL)',
            (self.workspace_id, digest, canonical_bytes([ref.model_dump(mode='json') for ref in request.scope_refs]).decode(), utc_now()))
        raw = canonical_bytes(value)
        ack = self.jobs.enqueue(raw.decode())
        self.connection.execute('INSERT INTO retrieval_jobs(job_id,workspace_id,scope_sha256,sequence,input_json,input_sha256) '
            'VALUES(?,?,?,COALESCE((SELECT MAX(sequence)+1 FROM retrieval_jobs WHERE workspace_id=? AND scope_sha256=?),1),?,?)',
            (ack.id, self.workspace_id, digest, self.workspace_id, digest, raw.decode(), sha256_bytes(raw)))
        return ack

    def generation(self, scope: sqlite3.Row | None) -> tuple[RetrievalIndexManifest, dict[str, tuple[str, ...]]] | None:
        if scope is None:
            return None
        generations = self.connection.execute('SELECT g.index_version,j.sequence FROM retrieval_generations g '
            'LEFT JOIN retrieval_jobs j ON j.job_id=g.job_id AND j.workspace_id=g.workspace_id AND j.scope_sha256=g.scope_sha256 '
            'WHERE g.workspace_id=? AND g.scope_sha256=? ORDER BY j.sequence',
            (self.workspace_id, scope['scope_sha256'])).fetchall()
        if (any(row['sequence'] is None for row in generations)
                or scope['index_version'] != (generations[-1]['index_version'] if generations else None)):
            raise index_integrity()
        if scope['index_version'] is None:
            return None
        return self.generation_by_id(scope['index_version'], scope['scope_sha256'])

    def generation_by_id(self, identifier: str, digest: str) -> tuple[RetrievalIndexManifest, dict[str, tuple[str, ...]]]:
        # SQL length check precedes loading large untrusted persisted JSON.
        size = self.connection.execute('SELECT length(CAST(manifest_json AS BLOB)) FROM retrieval_generations '
            'WHERE index_version=? AND workspace_id=? AND scope_sha256=?', (identifier, self.workspace_id, digest)).fetchone()
        if size is None or size[0] > SCOPE_BYTE_BUDGET + 1024 * 1024:
            raise index_integrity()
        row = self.connection.execute('SELECT * FROM retrieval_generations WHERE index_version=? AND workspace_id=? '
                                      'AND scope_sha256=?', (identifier, self.workspace_id, digest)).fetchone()
        manifest = checked_json(RetrievalIndexManifest, row['manifest_json'], row['manifest_sha256'])
        if (manifest.index_version != identifier or manifest.scope_sha256 != digest
                or manifest.descriptor.workspace_id != self.workspace_id or manifest.corpus_sha256 != row['corpus_sha256']
                or manifest.built_at != row['built_at']):
            raise index_integrity()
        job, value, result = self.job(row['job_id'])
        if (result is None or value.descriptor != manifest.descriptor or result.index_version != identifier
                or result.manifest_sha256 != row['manifest_sha256'] or result.built_at != manifest.built_at
                or result.indexed_block_count != len(manifest.blocks)
                or result.indexed_term_count != sum(block.term_count for block in manifest.blocks)):
            raise index_integrity()
        chunks = self.connection.execute('SELECT * FROM retrieval_chunks WHERE index_version=? ORDER BY chunk_id', (identifier,)).fetchall()
        if len(chunks) != len(manifest.blocks):
            raise index_integrity()
        indexed = {block.chunk_id: block for block in manifest.blocks}
        terms: dict[str, tuple[str, ...]] = {}
        for chunk in chunks:
            block = indexed.get(chunk['chunk_id'])
            tokens = tuple(chunk['tokens'].split(' ')) if chunk['tokens'] else ()
            try:
                actual_hash = terms_sha256(tokens)
            except (ValueError, TypeError):
                raise index_integrity() from None
            if (block is None or chunk['ref_json'] != canonical_bytes(block.ref).decode()
                    or actual_hash != chunk['terms_sha256'] or actual_hash != block.terms_sha256
                    or len(tokens) != block.term_count):
                raise index_integrity()
            terms[chunk['chunk_id']] = tokens
        fts = self.connection.execute('SELECT workspace_id,scope_sha256,index_version,chunk_id,tokens FROM retrieval_fts '
                                      'WHERE index_version=?', (identifier,)).fetchall()
        if len(fts) != len(terms) or len({item['chunk_id'] for item in fts}) != len(terms):
            raise index_integrity()
        for item in fts:
            if (item['workspace_id'] != self.workspace_id or item['scope_sha256'] != digest
                    or item['chunk_id'] not in terms or item['tokens'] != ' '.join(terms[item['chunk_id']])):
                raise index_integrity()
        return manifest, terms

    def match(self, manifest: RetrievalIndexManifest, terms: tuple[str, ...],
              block_terms: dict[str, tuple[str, ...]]) -> set[str]:
        # Safe typed-hex lexical terms are the only MATCH input, never raw query.
        terms_sha256(terms)
        expression = ' OR '.join('"' + term + '"' for term in terms)
        rows = self.connection.execute('SELECT chunk_id FROM retrieval_fts WHERE retrieval_fts MATCH ? '
            'AND workspace_id=? AND scope_sha256=? AND index_version=?',
            (expression, self.workspace_id, manifest.scope_sha256, manifest.index_version)).fetchall()
        found = {row[0] for row in rows}
        expected = {chunk for chunk, values in block_terms.items() if set(terms).intersection(values)}
        if found != expected or len(found) != len(rows):
            raise index_integrity()
        return found

    def publish(self, job_id: str, manifest: RetrievalIndexManifest, terms: dict[str, tuple[str, ...]]) -> RetrievalIndexJobResult:
        _, value, previous = self.job(job_id)
        if previous is not None or value.descriptor != manifest.descriptor:
            raise index_integrity()
        if set(terms) != {block.chunk_id for block in manifest.blocks}:
            raise index_integrity()
        raw = canonical_bytes(manifest)
        digest = sha256_bytes(raw)
        self.connection.execute('INSERT INTO retrieval_generations VALUES(?,?,?,?,?,?,?,?)',
            (manifest.index_version, self.workspace_id, manifest.scope_sha256, manifest.corpus_sha256,
             raw.decode(), digest, job_id, manifest.built_at))
        for block in manifest.blocks:
            values = terms[block.chunk_id]
            if terms_sha256(values) != block.terms_sha256 or len(values) != block.term_count:
                raise index_integrity()
            joined = ' '.join(values)
            self.connection.execute('INSERT INTO retrieval_chunks VALUES(?,?,?,?,?)',
                (block.chunk_id, manifest.index_version, canonical_bytes(block.ref).decode(), joined, block.terms_sha256))
            self.connection.execute('INSERT INTO retrieval_fts(workspace_id,scope_sha256,index_version,chunk_id,tokens) VALUES(?,?,?,?,?)',
                (self.workspace_id, manifest.scope_sha256, manifest.index_version, block.chunk_id, joined))
        result = RetrievalIndexJobResult(scope_sha256=manifest.scope_sha256, corpus_sha256=manifest.corpus_sha256,
            index_version=manifest.index_version, manifest_sha256=digest, indexed_block_count=len(manifest.blocks),
            indexed_term_count=sum(block.term_count for block in manifest.blocks), built_at=manifest.built_at)
        result_raw = canonical_bytes(result)
        self.connection.execute('UPDATE retrieval_jobs SET result_json=?,result_sha256=? WHERE job_id=? AND workspace_id=?',
            (result_raw.decode(), sha256_bytes(result_raw), job_id, self.workspace_id))
        self.connection.execute('UPDATE retrieval_scopes SET index_version=? WHERE workspace_id=? AND scope_sha256=?',
            (manifest.index_version, self.workspace_id, manifest.scope_sha256))
        return result
