"""Real HTTP-created source facts and post-transaction download admission."""
import sqlite3

import pytest

from services.api.app.infrastructure.import_worker import ImportWorker
from tests.integration.test_codex_artifact_import_http import selected, consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


@pytest.mark.parametrize('table', ['codex_import_batches', 'codex_import_bindings', 'codex_import_previews'])
@pytest.mark.parametrize('mutation', ['update', 'delete', 'replace', 'upsert'])
def test_original_import_source_rows_reject_normal_mutation_and_preserve_full_http_readback(consent_case, table, mutation):
    case, sid, _, body = selected(consent_case)
    created = case.post(f'sessions/{sid}/artifacts/import', body, 'original-import')
    assert created.status_code == 202
    identifier = created.json()['id']
    assert ImportWorker(case.app.state.database).run_once() is True
    original = case.get('artifact-imports/'+identifier)
    assert original.status_code == 200
    item = original.json()['items'][0]
    preview = case.client.get('/api/v1/imports/'+item['import_id'])
    assert preview.status_code == 200 and preview.json()['status'] == 'preview_ready'
    before = case.dump()
    with case.app.state.database.transaction() as conn:
        row = dict(conn.execute(f'SELECT * FROM {table}').fetchone())
        columns = ','.join(row)
        placeholders = ','.join('?' for _ in row)
        statement = f'INSERT OR REPLACE INTO {table}({columns}) VALUES({placeholders})'
        args = tuple(row.values())
        if mutation == 'update':
            statement, args = f'UPDATE {table} SET record_json=record_json', ()
        elif mutation == 'delete':
            statement, args = f'DELETE FROM {table}', ()
        elif mutation == 'upsert':
            statement = f'INSERT INTO {table}({columns}) VALUES({placeholders}) ON CONFLICT DO UPDATE SET record_json=excluded.record_json'
        with pytest.raises(sqlite3.IntegrityError, match='immutable Codex Import'):
            conn.execute(statement, args)
    assert case.dump() == before
    assert case.get('artifact-imports/'+identifier).content == original.content
    assert case.client.get('/api/v1/imports/'+item['import_id']).content == preview.content
    assert case.post(f'sessions/{sid}/artifacts/import', body, 'original-import').content == created.content
    assert len(case.app.state.synthetic_transport_calls) == 1
