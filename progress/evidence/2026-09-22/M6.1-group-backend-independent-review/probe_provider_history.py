"""One cache-only damaged-history reproduction. No real vendor or calculator."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path('<HOME>/.cache/learning-workbench-acceptance/m61-groups-active')
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from services.api.app.application.authoring_group_numeric_worker import GroupNumericWorker
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_authoring_group_numeric_service import generated_group, preview
from tests.integration.test_authoring_numeric_service import decision


def main():
    task = BASE/'probe-data'
    task.mkdir()
    generated = generated_group(task)
    database, identity, authoring, numeric, candidate, target, runtime = generated
    assert database.path.resolve().is_relative_to(task.resolve())
    original = authoring.draft(identity, candidate.draft_id)
    result = dict(scope='Synthetic real SQLite group, one complete-byte local HTTP response; no vendor and no calculator.',
                  before_draft_read='success', source_job_id=original.source_job_id,
                  candidate_sha256=candidate.candidate_sha256, runtime_kind='LedgerRuntime; no run method',
                  raw_body_logged=False, native_ports_used=False)
    with database.transaction() as conn:
        rows = conn.execute('SELECT sha256,bytes FROM provider_artifacts').fetchall()
        assert len(rows) == 1
        assert hashlib.sha256(bytes(rows[0]['bytes'])).hexdigest() == rows[0]['sha256']
        result['provider_artifact_original_sha256'] = rows[0]['sha256']
        # Deliberate damaged-history fixture in this private cache database only.
        # Keep the original stored digest/receipt/candidate untouched.
        conn.execute('DROP TRIGGER provider_artifacts_no_update')
        conn.execute('UPDATE provider_artifacts SET bytes=?', (b'corrupted original synthetic artifact',))
    try:
        authoring.draft(identity, candidate.draft_id)
    except ApiError as error:
        result['after_draft_read'] = dict(rejected=True, status=error.status, code=error.code)
    else:
        raise AssertionError('Protected draft read unexpectedly ignored damaged original Provider artifact')
    value = preview(generated)
    result['after_numeric_preview'] = dict(accepted=True, decision=value.decision, job=value.job,
                                          exact_candidate=value.candidate == candidate, exact_member=value.target == target)
    ack = numeric.decide(identity, value.id, decision(value), 'explicit-approve-damaged-history')
    assert ack.job is not None
    result['after_numeric_approval'] = dict(accepted=True, job_status=ack.job.status)
    worker = GroupNumericWorker(database, authoring.context, runtime)
    lease, job_input, actor = worker.claim()
    with database.transaction() as conn:
        checked = worker._access(conn, lease, job_input, actor)
        admitted = checked.begin(lease, utc_now())
        result['after_worker_original_access_guard_and_begin'] = dict(admitted=admitted)
    result['calculator_executed'] = False
    result['runtime_prepares'] = runtime.prepares
    result['runtime_checks'] = runtime.checks
    result['source_candidate_unchanged'] = candidate == value.candidate
    (BASE/'probe-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
