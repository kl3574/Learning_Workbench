"""Existing download HTTP with actual Import production and closed owner routing."""

import pytest

from tests.integration.test_import_http import block_preview, importing as importing, preview, upload


def imported_original(importing):
    app, client, settings = importing
    raw = b'# Synthetic artifact source\n\nExact original bytes.\n'
    staged = upload(client, settings, raw)
    candidate = preview(client, staged['import_id'])
    assert candidate['status'] == 'preview_ready'
    draft = block_preview(client, candidate)
    source = client.get('/api/v1/sources/' + draft['payload']['source_id'])
    assert source.status_code == 200
    return app, client, settings, staged, candidate, source.json()['artifact'], raw


def test_unregistered_artifact_profile_never_defaults_to_import(importing):
    app, client, _, _, _, artifact, raw = imported_original(importing)
    assert client.get(artifact['download_path']).content == raw
    with app.state.database.transaction() as connection:
        connection.execute("UPDATE artifacts SET profile='quality_report' WHERE id=?", (artifact['artifact_id'],))
    response = client.get(artifact['download_path'])
    assert response.status_code == 409
    assert response.json()['code'] == 'ARTIFACT_OWNER_UNAVAILABLE'
    assert raw not in response.content
