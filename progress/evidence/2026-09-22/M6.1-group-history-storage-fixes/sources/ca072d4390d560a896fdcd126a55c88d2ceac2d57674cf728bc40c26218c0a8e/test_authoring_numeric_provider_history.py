"""Numeric access must verify the original Provider bytes, including ACK replay.

Each case first completes real CheckedDispatch against a controlled loopback
provider. Only its stored artifact bytes are then damaged. LedgerRuntime has no
executor: these tests never run a numeric process or call a real vendor.
"""

from dataclasses import dataclass
import json

import pytest

from packages.contracts.canonical import sha256_bytes
from services.api.app.application.authoring_group_numeric_worker import GroupNumericWorker
from services.api.app.application.authoring_numeric_worker import NumericWorker
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_dispatch import CheckedDispatch
from services.api.app.authoring_dto import NumericCheckPreviewWrite
from services.api.app.authoring_group_dto import AuthoringGroupNumericPreviewWrite
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_authoring_group_numeric_service import generated_group
from tests.integration.test_authoring_numeric_service import decision, generated as old_generated
from tests.integration.test_retrieval import all_rows


def table_hashes(database):
    """Compare every table without allowing pytest to print session/secret rows."""
    return {name: sha256_bytes(repr(rows).encode()) for name, rows in all_rows(database).items()}


def rejected(call):
    with pytest.raises(ApiError) as caught:
        call()
    assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')


@dataclass(repr=False)
class ProviderHistoryCase:
    variant: str
    state: tuple

    def __repr__(self):
        return f'<controlled {self.variant} Provider-history case; no identity repr>'

    @property
    def database(self):
        return self.state[0]

    @property
    def identity(self):
        return self.state[1]

    @property
    def authoring(self):
        return self.state[2]

    @property
    def numeric(self):
        return self.state[3]

    @property
    def candidate(self):
        return self.state[4]

    @property
    def runtime(self):
        return self.state[-1]

    def preview(self, key='original-numeric-preview'):
        if self.variant == 'group':
            target = self.state[5]
            return self.numeric.preview(self.identity, self.candidate.draft_id, target.member_key,
                AuthoringGroupNumericPreviewWrite(candidate=self.candidate, target=target), key)
        return self.numeric.preview(self.identity, self.candidate.draft_id,
            NumericCheckPreviewWrite(candidate=self.candidate), key)

    def worker(self):
        worker = GroupNumericWorker if self.variant == 'group' else NumericWorker
        return worker(self.database, self.authoring.context, self.runtime)

    def damage_original_artifact(self):
        draft = self.authoring.draft(self.identity, self.candidate.draft_id)
        view = self.authoring.read(self.identity, draft.source_job_id)
        assert view.summary.candidate == self.candidate
        assert isinstance(self.authoring.provider, CheckedDispatch)
        assert view.consent_id is not None and view.provider_receipt_id is not None
        before = table_hashes(self.database)
        with self.database.transaction() as conn:
            checked = self.authoring.provider.read_result(conn, self.identity, draft.source_job_id, view.consent_id)
            assert checked is not None and checked.answer is not None
            assert checked.receipt.id == view.provider_receipt_id
            rows = conn.execute('SELECT * FROM provider_artifacts').fetchall()
            assert len(rows) == 1
            row = rows[0]
            original = bytes(row['bytes'])
            assert row['channel'] == 'answer'
            assert sha256_bytes(original) == row['sha256']
            assert checked.answer.text.encode() == original
            metadata = {key: row[key] for key in row.keys() if key != 'bytes'}
            # Private fault fixture only: leave the receipt, declared digest,
            # candidate, permissions and all numeric history exactly unchanged.
            conn.execute('DROP TRIGGER provider_artifacts_no_update')
            conn.execute('UPDATE provider_artifacts SET bytes=? WHERE id=?',
                (b'!' + original[1:], row['id']))
            damaged = conn.execute('SELECT * FROM provider_artifacts WHERE id=?', (row['id'],)).fetchone()
            assert {key: damaged[key] for key in damaged.keys() if key != 'bytes'} == metadata
            assert sha256_bytes(bytes(damaged['bytes'])) != row['sha256']
        after = table_hashes(self.database)
        assert {name for name in before if before[name] != after[name]} == {'provider_artifacts'}
        # Positive failure control: the existing actual Authoring owner already
        # rejects this precise original-artifact corruption, without mutation.
        rejected(lambda: self.authoring.draft(self.identity, self.candidate.draft_id))
        assert table_hashes(self.database) == after
        return after


@pytest.fixture(params=['single', 'group'])
def generated_history(request, tmp_path):
    state = generated_group(tmp_path) if request.param == 'group' else old_generated.__wrapped__(tmp_path)
    return ProviderHistoryCase(request.param, state)


@pytest.mark.parametrize('operation', ['preview', 'preview_replay', 'read', 'approve_pending', 'approve_replay'])
def test_numeric_subject_operations_reject_damaged_original_provider_bytes(generated_history, operation):
    case = generated_history
    value = case.preview() if operation != 'preview' else None
    if operation == 'approve_replay':
        ack = case.numeric.decide(case.identity, value.id, decision(value), 'original-approve')
        assert ack.job is not None and ack.job.status == 'queued'
    before = case.damage_original_artifact()
    runtime_before = (case.runtime.prepares, case.runtime.checks)
    def call():
        if operation in {'preview', 'preview_replay'}:
            return case.preview()
        if operation == 'read':
            return case.numeric.read(case.identity, value.id)
        return case.numeric.decide(case.identity, value.id, decision(value), 'original-approve')
    rejected(call)
    assert table_hashes(case.database) == before
    assert (case.runtime.prepares, case.runtime.checks) == runtime_before


def test_numeric_worker_rechecks_original_provider_bytes_before_launch_permission(generated_history):
    case = generated_history
    value = case.preview()
    ack = case.numeric.decide(case.identity, value.id, decision(value), 'original-approve')
    assert ack.job is not None and ack.job.status == 'queued'
    worker = case.worker()
    work = worker.claim()
    assert work is not None and work[0].job_id == ack.job.id
    lease, job_input, actor = work
    before = case.damage_original_artifact()
    runtime_before = (case.runtime.prepares, case.runtime.checks)
    with case.database.transaction() as conn:
        # If the guard accidentally returns, this would admit a durable launch.
        # The failing pytest context rolls the transaction back in the RED run.
        with pytest.raises(ApiError) as caught:
            repo = worker._access(conn, lease, job_input, actor)
            repo.begin(lease, utc_now())
        assert (caught.value.status, caught.value.code) == (503, 'PROVIDER_INTEGRITY_INVALID')
    assert table_hashes(case.database) == before
    assert (case.runtime.prepares, case.runtime.checks) == runtime_before
    with case.database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM authoring_numeric_executions').fetchone()[0] == 0


def test_safe_numeric_job_read_and_cancel_do_not_require_private_provider_bytes(generated_history):
    case = generated_history
    value = case.preview()
    ack = case.numeric.decide(case.identity, value.id, decision(value), 'original-approve')
    assert ack.job is not None
    before = case.damage_original_artifact()
    runtime_before = (case.runtime.prepares, case.runtime.checks)
    safe = case.numeric.job(case.identity, ack.job.id)
    assert safe.id == ack.job.id and safe.status == 'queued'
    assert safe.result_refs == safe.warnings == [] and safe.error is None
    assert table_hashes(case.database) == before
    body = JobCancelRequest(expected_revision=safe.revision)
    cancelled = case.numeric.cancel_job(case.identity, safe.id, body, 'original-safe-cancel')
    assert cancelled.status == 'cancelled'
    assert cancelled.result_refs == cancelled.warnings == [] and cancelled.error is None
    after = table_hashes(case.database)
    assert case.numeric.job(case.identity, safe.id) == cancelled
    assert case.numeric.cancel_job(case.identity, safe.id, body, 'original-safe-cancel') == cancelled
    assert table_hashes(case.database) == after
    assert (case.runtime.prepares, case.runtime.checks) == runtime_before
    with case.database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_dispatches').fetchone()[0] == 1
        rows = conn.execute('SELECT start_json,end_json FROM authoring_numeric_executions').fetchall()
        assert len(rows) == 1  # Explicit queued cancellation records a no-launch terminal.
        start, end = json.loads(rows[0]['start_json']), json.loads(rows[0]['end_json'])
        assert start['admitted_at'] is None and start['actual_started_at'] is None
        assert end['result']['outcome'] == 'cancelled' and end['result']['verdict'] == 'BLOCKED'
        assert end['result']['started_at'] is None and end['result']['exit_code'] is None
