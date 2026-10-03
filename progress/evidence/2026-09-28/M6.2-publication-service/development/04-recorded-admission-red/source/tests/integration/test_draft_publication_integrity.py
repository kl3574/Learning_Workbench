"""Synthetic damage and current-access changes against real persisted publication."""
import json

import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from tests.integration.test_draft_publication import workflow as workflow, ready
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def test_rehashed_result_cannot_invent_a_success_without_original_required_warning_ack(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    service.publish(identity, candidate.draft_id, body, 'published')
    with database.transaction() as conn:
        row = conn.execute('SELECT publication_id,record_json FROM draft_publication_results').fetchone()
        raw = json.loads(row['record_json'])
        raw['request']['acknowledged_warning_codes'] = []
        raw['admission']['acknowledged_warning_codes'] = []
        corrupted = canonical_bytes(raw)
        conn.execute('DROP TRIGGER draft_publication_results_no_update')
        conn.execute('UPDATE draft_publication_results SET record_json=?,sha256=? WHERE publication_id=?',
                     (corrupted.decode(), sha256_bytes(corrupted), row['publication_id']))
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body.model_copy(update={'acknowledged_warning_codes': []}), 'published')
    assert table_hashes(database) == before
