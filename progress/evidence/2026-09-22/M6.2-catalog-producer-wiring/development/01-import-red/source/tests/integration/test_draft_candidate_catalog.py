"""Actual producers register immutable identities; lookup never repairs or approves."""

import pytest

from tests.integration.test_draft_candidate_owners import imported_candidate as original_import_fixture


@pytest.fixture
def imported_candidate(tmp_path):
    yield from original_import_fixture.__wrapped__(tmp_path)


def test_real_import_preview_already_has_exact_catalog_identity(imported_candidate):
    database, identity, _, _, _, candidate = imported_candidate
    with database.transaction(immediate=False) as connection:
        row = connection.execute(
            'SELECT i.workspace_id,i.owner,i.source_kind,i.entity,r.draft_revision,r.candidate_sha256 '
            'FROM draft_candidate_identities i JOIN draft_candidate_revisions r USING(draft_id) '
            'WHERE i.draft_id=?', (candidate.draft_id,),
        ).fetchone()
        assert row is not None
        assert tuple(row) == (identity.workspace_id, 'import', 'import', 'block', 1, candidate.candidate_sha256)
