"""Malformed trusted-port values fail closed before serializing private diagnostics."""
import warnings

import pytest

from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
from tests.integration.test_review_materials import material_case, read_case, table_hashes
from tests.integration.test_review_job_lifecycle import prepared

__all__ = ['material_case', 'prepared']


@pytest.mark.parametrize('entry', ['material', 'candidate'])
def test_candidate_owner_boundary_suppresses_malformed_serialization(material_case, monkeypatch, entry):
    case = material_case
    marker = 'synthetic-private-review-boundary'
    material = read_case(case)
    facade = DraftCandidates({case.kind: case.owner})
    if entry == 'material':
        bad = material.model_copy(update={'payload': {'unexpected': marker}})
        monkeypatch.setattr(case.owner, 'read_review_material', lambda *args: bad)
    else:
        bad = case.candidate.model_copy(update={'draft_id': {'unexpected': marker}})
    before = table_hashes(case.database)
    with case.database.transaction() as connection, warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter('always')
        with pytest.raises(ApiError) as caught:
            if entry == 'material':
                facade.read_review_material(connection, case.identity, case.candidate.draft_id, case.candidate.draft_revision)
            else:
                facade.admit(connection, case.identity, case.kind, bad)
    expected = (503, 'DRAFT_OWNER_INTEGRITY') if entry == 'material' else (422, 'SCHEMA_INVALID')
    assert (caught.value.status, caught.value.code) == expected
    assert marker not in str(caught.value) and marker not in repr(caught.value)
    assert not emitted, 'Malformed owner input must not produce serializer warnings'
    assert table_hashes(case.database) == before


def test_job_input_boundary_rejects_malformed_request_without_warning_or_job(prepared):
    database, identity, value = prepared
    marker = 'synthetic-private-review-job-request'
    malformed = value.model_copy(update={'request': {'reviewer_note': marker}})
    before = table_hashes(database)
    with database.transaction() as connection, warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter('always')
        with pytest.raises(ApiError) as caught:
            ReviewJobRepository(connection, identity.workspace_id).create(value.review_id, 'draft_review', malformed)
    assert (caught.value.status, caught.value.code) == (409, 'AUTHORING_INTEGRITY_ERROR')
    assert marker not in str(caught.value) and marker not in repr(caught.value)
    assert not emitted, 'Malformed Review input must not produce serializer warnings'
    assert table_hashes(database) == before
