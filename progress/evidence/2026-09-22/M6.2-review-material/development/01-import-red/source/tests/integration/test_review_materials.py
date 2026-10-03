"""Complete owner materials from actual producers; no review decision or vendor call."""

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.draft_candidates import DraftCandidates
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_draft_candidate_owners import imported_candidate as imported_candidate


def checked_read(database, identity, owner, source_kind, candidate, monkeypatch):
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        changes = conn.total_changes
        with monkeypatch.context() as patch:
            def unexpected_connection():
                pytest.fail('Review material must use the caller transaction')
            patch.setattr(database, 'connect', unexpected_connection)
            candidates = DraftCandidates({source_kind: owner})
            resolved = candidates.lookup(conn, identity, candidate.draft_id, candidate.draft_revision)
            material = candidates.read_review_material(conn, identity, candidate.draft_id, candidate.draft_revision)
            assert material.candidate == resolved.candidate
            assert conn.in_transaction and conn.total_changes == changes
    assert table_hashes(database) == before
    raw = material.model_dump(mode='json')
    digest = raw.pop('descriptor_sha256')
    assert sha256_bytes(canonical_bytes(raw)) == digest
    return material


def test_real_import_material_preserves_body_and_excludes_private_solutions(imported_candidate, monkeypatch):
    database, identity, owner, staged, draft, candidate = imported_candidate
    value = checked_read(database, identity, owner, 'import', candidate, monkeypatch)
    assert value.payload.payload == draft.payload
    assert value.payload.import_id == staged.import_id
    assert value.payload.original_input_sha256 == staged.input_sha256
    assert value.payload.private_solution_coverage == 'excluded'
    assert value.payload.payload.body_markdown == '# Synthetic source\n\nOriginal public body.\n'
    assert 'state' not in value.payload.model_dump()
