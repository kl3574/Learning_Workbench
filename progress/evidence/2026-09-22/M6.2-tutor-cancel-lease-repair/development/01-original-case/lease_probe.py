"""Private deterministic scheduling probe; uses the real worker watch and HTTP case."""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def lease_renew_window(request, monkeypatch):
    if request.node.name != 'test_cancel_during_actual_http_stops_once_and_preserves_real_dispatch_facts':
        return
    from services.api.app.application.tutor import TutorService
    from services.api.app.infrastructure.tutor_job_repository import TutorLease
    from services.api.app.infrastructure.tutor_repository import TutorRepository
    module = request.module
    configured = module.configured
    original_cancel = TutorService.cancel
    workers = []
    def capture(*args, **kwargs):
        result = configured(*args, **kwargs)
        workers.append(result[0])
        return result
    def cancel(service, identity, identifier, body, key):
        if key == 'cancel-actual-http':
            with service.database.transaction(immediate=False) as connection:
                before = TutorRepository(connection, identity.workspace_id).source_state(identifier)
            assert before.status == 'running' and not before.cancel_requested
            lease = TutorLease(identifier, identity.workspace_id, before.lease_owner,
                               before.job_revision, before.lease_until)
            worker = workers[-1]
            assert worker._watch(worker._identity(identity.workspace_id), lease)
            with service.database.transaction(immediate=False) as connection:
                renewed = TutorRepository(connection, identity.workspace_id).source_state(identifier)
            assert renewed.lease_owner == before.lease_owner
            assert renewed.lease_until > before.lease_until
            Path(os.environ['LEASE_PROBE_FACTS']).write_text(json.dumps({
                'actual_watch_called': True, 'cancel_requested_before': before.cancel_requested,
                'same_owner': renewed.lease_owner == before.lease_owner,
                'same_job_revision': renewed.job_revision == before.job_revision,
                'lease_until_before': before.lease_until, 'lease_until_after_watch': renewed.lease_until,
                'scheduled_before_service_cancel_transaction': True,
            }, indent=2) + '\n')
        return original_cancel(service, identity, identifier, body, key)
    monkeypatch.setattr(module, 'configured', capture)
    monkeypatch.setattr(TutorService, 'cancel', cancel)
