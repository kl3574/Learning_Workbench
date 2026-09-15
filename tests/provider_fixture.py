"""Test-only SQLite owner of real prepared source jobs and exact public refs.

No production source or model is registered by this helper. Its original
synthetic text is not evidence of model quality or a production Tutor workflow.
All positive dispatch tests must still pass the actual Provider services.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, snapshot_sha256, strict_json
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_models import DispatchLease, PreparedOutboundMaterial
from services.api.app.application.provider_ports import OutboundSourceRegistry, SourcePreparationChanged
from services.api.app.infrastructure.blobs import BlobStore
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import ContentRepository, reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.security import (
    SessionIdentity, consume_bootstrap, guard_subject_access, issue_bootstrap_code,
)
from services.api.app.provider_dto import ReferenceSummary
from tests.practice_fixtures import practice_fixture


SOURCE_KIND = 'test_provider_source'


def prepared_digest(workspace_id: str, material: PreparedOutboundMaterial) -> str:
    return sha256_bytes(canonical_bytes({
        'version': 'prepared-outbound-v1', 'workspace_id': workspace_id,
        'job_id': material.job_id, 'source_input_sha256': material.job_input_sha256,
        'purpose': material.purpose,
        'context_snapshot': material.context_snapshot.model_dump(mode='json'),
        'messages': [value.model_dump(mode='json') for value in material.messages],
        'evidence': [value.model_dump(mode='json') for value in material.evidence],
        'preparation_version': material.preparation_version,
    }))


def source_invalid() -> ApiError:
    return ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '测试来源的持久材料完整性校验失败。')


class PersistedProviderSource:
    def __init__(self, database: Database):
        self.database = database

    def initialize(self) -> None:
        with self.database.transaction() as connection:
            connection.execute('''CREATE TABLE test_provider_sources(
                job_id TEXT PRIMARY KEY REFERENCES jobs(id), workspace_id TEXT NOT NULL,
                material_json TEXT NOT NULL, consent_id TEXT,
                material_sha256 TEXT NOT NULL)''')
            connection.execute('''CREATE TABLE test_provider_preparations(
                job_id TEXT NOT NULL, material_sha256 TEXT NOT NULL, material_json TEXT NOT NULL,
                PRIMARY KEY(job_id, material_sha256))''')
            connection.execute('''CREATE TABLE test_provider_proposals(
                proposal_id TEXT PRIMARY KEY, job_id TEXT NOT NULL,
                prepared_input_sha256 TEXT NOT NULL)''')

    def create_job(self, identity: SessionIdentity, *, message: str = '说明示例中的量与单位。') -> str:
        fixture = practice_fixture('providersource', profile='learner')
        body = fixture.bodies[fixture.block.body_path]
        info = BlobStore(self.database.settings.data_dir).write(body, fixture.block.body_sha256)
        identifier = 'job_' + uuid4().hex
        now = utc_now()
        ref = reference(fixture.block)
        job_input = {'message': message, 'ref': ref.model_dump(mode='json'), 'purpose': 'tutor'}
        digest = sha256_bytes(canonical_bytes(job_input))
        context = dm.ContextSnapshot(id='context_' + uuid4().hex, created_at=now,
            request_sha256=digest, resolved_refs=[ref], policy='learning',
            character_count=len(body.decode()) + len(message), snapshot_sha256='0' * 64)
        context = context.model_copy(update={'snapshot_sha256': snapshot_sha256(context)})
        material = PreparedOutboundMaterial(job_id=identifier, job_revision=1, job_input_sha256=digest,
            purpose='tutor', context_snapshot=context,
            messages=[dm.GenerationMessage(role='user', content=message)],
            evidence=[dm.EvidenceChunk(ref=ref, locator='原始合成块全文', text=body.decode())],
            preparation_version='test-persisted-source-v1', prepared_input_sha256='0' * 64)
        material = material.model_copy(update={'prepared_input_sha256': prepared_digest(identity.workspace_id, material)})
        with self.database.transaction() as connection:
            guard_subject_access(connection, identity.workspace_id)
            repository = ContentRepository(connection, identity.workspace_id)
            if connection.execute('SELECT 1 FROM objects WHERE id=?', (fixture.block.id,)).fetchone() is None:
                repository.insert_revisions(fixture.public_objects, {info.sha256: info})
                for value in fixture.public_objects:
                    repository.advance(value)
            connection.execute('''INSERT INTO context_snapshots
                (id,workspace_id,snapshot_sha256,envelope_json,created_at) VALUES(?,?,?,?,?)''',
                (context.id, identity.workspace_id, context.snapshot_sha256, canonical_bytes(context).decode(), now))
            connection.execute('''INSERT INTO jobs
                (id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at)
                VALUES(?,?,?,'awaiting_approval',1,?,?,?,?)''',
                (identifier, identity.workspace_id, SOURCE_KIND, digest, canonical_bytes(job_input).decode(), now, now))
            connection.execute('INSERT INTO test_provider_sources VALUES(?,?,?,NULL,?)',
                (identifier, identity.workspace_id, canonical_bytes(material).decode(), material.prepared_input_sha256))
            connection.execute('INSERT INTO test_provider_preparations VALUES(?,?,?)',
                (identifier, material.prepared_input_sha256, canonical_bytes(material).decode()))
        return identifier

    def _row(self, transaction: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> sqlite3.Row:
        if not transaction.in_transaction:
            raise AssertionError('source methods require an actual caller transaction')
        guard_subject_access(transaction, identity.workspace_id)
        row = transaction.execute('''SELECT j.*,s.material_json,s.material_sha256,s.consent_id
            FROM jobs j JOIN test_provider_sources s ON s.job_id=j.id
            WHERE j.id=? AND j.workspace_id=? AND s.workspace_id=j.workspace_id AND j.kind=?''',
            (job_id, identity.workspace_id, SOURCE_KIND)).fetchone()
        if row is None:
            raise ApiError(404, 'JOB_MISSING', '测试来源任务不存在或不可访问。')
        return row

    def _checked(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                 job_id: str) -> tuple[sqlite3.Row, PreparedOutboundMaterial]:
        row = self._row(transaction, identity, job_id)
        try:
            material = PreparedOutboundMaterial.model_validate(strict_json(row['material_json']))
            self._historical(transaction, identity, material)
            original = strict_json(row['input_json'])
            if (material.job_id != job_id or material.job_input_sha256 != row['input_sha256']
                    or sha256_bytes(canonical_bytes(original)) != row['input_sha256']
                    or material.prepared_input_sha256 != row['material_sha256']
                    or prepared_digest(identity.workspace_id, material) != row['material_sha256']):
                raise source_invalid()
            context = material.context_snapshot
            stored_context = transaction.execute('SELECT * FROM context_snapshots WHERE id=? AND workspace_id=?',
                (context.id, identity.workspace_id)).fetchone()
            if (stored_context is None or snapshot_sha256(context) != context.snapshot_sha256
                    or stored_context['snapshot_sha256'] != context.snapshot_sha256
                    or canonical_bytes(context).decode() != stored_context['envelope_json']
                    or context.resolved_refs != [e.ref for e in material.evidence]):
                raise source_invalid()
            repository = ContentRepository(transaction, identity.workspace_id)
            for evidence in material.evidence:
                value = repository.load(evidence.ref.entity, evidence.ref.id, evidence.ref.revision).value
                if not isinstance(value, dm.ContentBlock) or reference(value) != evidence.ref:
                    raise source_invalid()
                body = repository.body_info(value)
                if BlobStore(self.database.settings.data_dir).read(body.sha256, body.size).decode() != evidence.text:
                    raise source_invalid()
        except (ValueError, KeyError, TypeError):
            raise source_invalid() from None
        return row, material

    def _historical(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                    material: PreparedOutboundMaterial) -> None:
        row = transaction.execute('SELECT material_json FROM test_provider_preparations WHERE job_id=? AND material_sha256=?',
            (material.job_id, material.prepared_input_sha256)).fetchone()
        if row is None or prepared_digest(identity.workspace_id, material) != material.prepared_input_sha256:
            raise source_invalid()
        stored = PreparedOutboundMaterial.model_validate(strict_json(row['material_json']))
        if stored.model_dump(exclude={'job_revision'}) != material.model_dump(exclude={'job_revision'}):
            raise source_invalid()

    def advance_preparation(self, identity: SessionIdentity, job_id: str) -> None:
        """A test-only owner upgrade preserves original input and both preparations."""
        with self.database.transaction() as connection:
            row, material = self._checked(connection, identity, job_id)
            self._available(row)
            if material.preparation_version != 'test-persisted-source-v1':
                raise ValueError('Only the defined fixture v1 to v2 upgrade is supported.')
            updated = material.model_copy(update={'preparation_version': 'test-persisted-source-v2'})
            updated = updated.model_copy(update={'prepared_input_sha256': prepared_digest(identity.workspace_id, updated)})
            connection.execute('INSERT INTO test_provider_preparations VALUES(?,?,?)',
                (job_id, updated.prepared_input_sha256, canonical_bytes(updated).decode()))
            connection.execute('UPDATE test_provider_sources SET material_json=?,material_sha256=? WHERE job_id=?',
                (canonical_bytes(updated).decode(), updated.prepared_input_sha256, job_id))
            connection.execute('UPDATE jobs SET revision=revision+1 WHERE id=?', (job_id,))

    def read_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, expected_job_revision: int) -> PreparedOutboundMaterial:
        row, material = self._checked(transaction, identity, job_id)
        if row['revision'] != expected_job_revision:
            raise ApiError(412, 'REVISION_CONFLICT', '任务预览基准已改变。')
        self._available(row)
        return material.model_copy(update={'job_revision': row['revision']})

    @staticmethod
    def _available(row: sqlite3.Row) -> None:
        if row['status'] not in {'queued', 'running', 'awaiting_approval'} or row['cancel_requested']:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '测试来源不在可授权或运行阶段。')

    def verify_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial) -> None:
        row, original = self._checked(transaction, identity, material.job_id)
        self._historical(transaction, identity, material)
        if original.model_dump(exclude={'job_revision'}) != material.model_dump(exclude={'job_revision'}):
            raise SourcePreparationChanged()
        self._available(row)

    def reference_summaries(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            material: PreparedOutboundMaterial) -> list[ReferenceSummary]:
        self.verify_prepared(transaction, identity, material)
        repository = ContentRepository(transaction, identity.workspace_id)
        return [ReferenceSummary(ref=item.ref,
            title=repository.load(item.ref.entity, item.ref.id, item.ref.revision).value.title,
            locator=item.locator, character_count=len(item.text), excerpt_sha256=sha256_bytes(item.text.encode()))
            for item in material.evidence]

    def bind_authorization(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                           job_id: str, prepared_input_sha256: str, consent_id: str) -> None:
        row, material = self._checked(transaction, identity, job_id)
        self._available(row)
        if material.prepared_input_sha256 != prepared_input_sha256:
            raise source_invalid()
        transaction.execute('UPDATE test_provider_sources SET consent_id=? WHERE job_id=? AND workspace_id=?',
                            (consent_id, job_id, identity.workspace_id))

    def record_proposal(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        job_id: str, prepared_input_sha256: str, proposal_id: str) -> None:
        row, material = self._checked(transaction, identity, job_id)
        self._available(row)
        if material.prepared_input_sha256 != prepared_input_sha256:
            raise source_invalid()
        from services.api.app.infrastructure.consent_repository import ConsentRepository
        view, prepared, _ = ConsentRepository(transaction, identity.workspace_id).proposal_material(proposal_id)
        if prepared.prepared_input_sha256 != prepared_input_sha256 or view.summary.job_id != job_id:
            raise source_invalid()
        transaction.execute('INSERT OR IGNORE INTO test_provider_proposals VALUES(?,?,?)',
                            (proposal_id, job_id, prepared_input_sha256))

    def verify_output(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, dispatch_id: str) -> None:
        from services.api.app.application.policy import Policy
        from services.api.app.infrastructure.consent_repository import ConsentRepository
        Policy(transaction, identity.workspace_id).check('private_artifact')
        row, _ = self._checked(transaction, identity, job_id)
        record = ConsentRepository(transaction, identity.workspace_id).read_dispatch(dispatch_id)
        if record.job_id != job_id or record.consent_id != row['consent_id']:
            raise source_invalid()

    def claim(self, identity: SessionIdentity, job_id: str) -> DispatchLease:
        until = (datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')
        owner = 'worker_' + uuid4().hex
        with self.database.transaction() as connection:
            row, _ = self._checked(connection, identity, job_id)
            self._available(row)
            if row['consent_id'] is None:
                raise ApiError(409, 'CONSENT_REQUIRED', '测试来源尚未绑定实际许可。')
            connection.execute("UPDATE jobs SET status='running',revision=revision+1,lease_owner=?,lease_until=? WHERE id=?",
                               (owner, until, job_id))
        return DispatchLease(owner_id=owner, job_revision=row['revision'] + 1, expires_at=until)

    def cancel(self, identity: SessionIdentity, job_id: str) -> None:
        """Test source owner transition, used to exercise actual assessment exclusion."""
        with self.database.transaction() as connection:
            self._checked(connection, identity, job_id)
            connection.execute("UPDATE jobs SET status='cancelled',cancel_requested=1,revision=revision+1 "
                               'WHERE id=? AND workspace_id=?', (job_id, identity.workspace_id))

    def verify_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial, lease: DispatchLease,
                        consent_id: str) -> dm.JobRef:
        self.verify_prepared(transaction, identity, material)
        row = self._row(transaction, identity, material.job_id)
        if (row['consent_id'] != consent_id or row['status'] != 'running' or row['revision'] != lease.job_revision
                or row['lease_owner'] != lease.owner_id or row['lease_until'] != lease.expires_at
                or datetime.fromisoformat(lease.expires_at.replace('Z', '+00:00')) <= datetime.now(UTC)):
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '测试来源租约已失效。')
        return dm.JobRef(id=material.job_id, status=row['status'])

    def read_job(self, transaction: sqlite3.Connection, identity: SessionIdentity, job_id: str) -> dm.JobRef:
        row, _ = self._checked(transaction, identity, job_id)
        return dm.JobRef(id=job_id, status=row['status'])


def provider_source(tmp_path: Path) -> tuple[Database, SessionIdentity, PersistedProviderSource, OutboundSourceRegistry, str]:
    database = Database(Settings(data_dir=tmp_path / 'provider-data'))
    database.initialize()
    _, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    source = PersistedProviderSource(database)
    source.initialize()
    identifier = source.create_job(identity)
    return database, identity, source, OutboundSourceRegistry({SOURCE_KIND: source}), identifier
