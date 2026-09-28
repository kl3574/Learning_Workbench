"""Actual owner material enters deterministic checks; no review/human receipt."""
import copy
import warnings

import pytest
from pydantic import ValidationError

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.review_checks import (
    ORDER, StructuralReviewReport, review_structure,
)
from services.api.app.application.review_material_models import CheckedReviewMaterial
from tests.integration.test_review_materials import (
    MaterialCase, import_fixture, single_fixture, generated_group, read_case, table_hashes,
)


@pytest.fixture(params=['import', 'single', 'lesson', 'practice_set', 'assessment'])
def actual_material(request, tmp_path):
    kind = request.param
    if kind == 'import':
        for database, identity, owner, _, _, candidate in import_fixture.__wrapped__(tmp_path):
            case = MaterialCase(database, identity, owner, candidate, 'import')
            yield case, read_case(case)
    else:
        state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
        database, identity, owner, _, candidate, *_ = state
        case = MaterialCase(database, identity, owner, candidate,
                            'authoring_single' if kind == 'single' else 'authoring_group', state)
        yield case, read_case(case)


def test_current_real_owner_material_reports_only_its_actual_declaration_scope(actual_material):
    case, material = actual_material
    before = table_hashes(case.database)
    original = canonical_bytes(material)
    result = review_structure(material, requested=True)
    assert result.candidate == material.candidate
    assert result.material_descriptor_sha256 == material.descriptor_sha256
    assert result.structural == 'PASS'
    assert [check.code for check in result.checks] == list(ORDER)
    assert [check.status for check in result.checks] == (
        ['PASS', 'PASS', 'NOT_RUN', 'NOT_RUN'] if case.kind == 'import' else ['PASS'] * 4)
    assert canonical_bytes(material) == original and table_hashes(case.database) == before
    # The serialized result has no payload, answer, numeric execution, human
    # verdict, provider identity or fabricated ReviewReceipt identity.
    assert set(result.model_dump()) == {
        'version', 'candidate', 'material_descriptor_sha256', 'requested', 'structural', 'checks'}


def test_unrequested_structure_is_not_run_even_when_input_was_validated(actual_material):
    _, material = actual_material
    result = review_structure(material, requested=False)
    assert result.structural == 'NOT_RUN'
    assert all(check.status == 'NOT_RUN' and check.detail_code == 'not_requested' for check in result.checks)


def test_bypassed_material_validation_is_integrity_error_without_receipt(actual_material):
    case, material = actual_material
    before = table_hashes(case.database)
    malformed = material.model_copy(update={'descriptor_sha256': '0' * 64})
    with pytest.raises(ApiError) as caught:
        review_structure(malformed, requested=True)
    assert caught.value.code == 'REVIEW_MATERIAL_INTEGRITY'
    assert table_hashes(case.database) == before


def test_malformed_nested_material_does_not_emit_private_serialization_warning(actual_material):
    case, material = actual_material
    marker = 'synthetic-private-structure-marker'
    malformed = material.model_copy(update={'payload': {'unexpected': marker}})
    before = table_hashes(case.database)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter('always')
        with pytest.raises(ApiError) as caught:
            review_structure(malformed, requested=True)
    assert (caught.value.status, caught.value.code) == (503, 'REVIEW_MATERIAL_INTEGRITY')
    assert marker not in str(caught.value)
    assert marker not in ''.join(str(item.message) for item in observed)
    assert observed == []
    assert table_hashes(case.database) == before


def test_self_consistent_foreign_declared_source_is_fail_without_owner_authentication(tmp_path):
    # This is deliberately synthesized from real material after the owner read.
    # Recomputing its hashes does not make it authenticated owner history.
    state = single_fixture.__wrapped__(tmp_path)
    database, identity, owner, _, candidate, *_ = state
    case = MaterialCase(database, identity, owner, candidate, 'authoring_single', state)
    material = read_case(case)
    raw = material.model_dump(mode='json')
    record = raw['payload']['record']
    record['payload']['declared_source_refs'] = [
        {'entity': 'block', 'id': 'block_unprepared', 'revision': 1, 'sha256': 'a' * 64}]
    candidate_sha = sha256_bytes(canonical_bytes(record['payload']))
    record['candidate']['candidate_sha256'] = candidate_sha
    raw['candidate']['candidate_sha256'] = candidate_sha
    raw['owner_record_sha256'] = sha256_bytes(canonical_bytes(record))
    raw['descriptor_sha256'] = sha256_bytes(canonical_bytes({k: v for k, v in raw.items() if k != 'descriptor_sha256'}))
    synthetic = CheckedReviewMaterial.model_validate(raw)
    result = review_structure(synthetic, requested=True)
    assert result.structural == 'FAIL'
    assert result.checks[2].status == 'FAIL'
    assert result.checks[2].detail_code == 'declared_source_outside_prepared_set'
    # Actual owner material and immutable history remain unchanged.
    assert read_case(case) == material


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'aggregate', 'unrequested', 'detail', 'verdict', 'raw_text'])
def test_report_cannot_hide_scope_or_failed_check(actual_material, damage):
    _, material = actual_material
    raw = review_structure(material, requested=True).model_dump(mode='python')
    if damage == 'missing':
        raw['checks'].pop()
    elif damage == 'duplicate':
        raw['checks'][1] = copy.deepcopy(raw['checks'][0])
    elif damage == 'aggregate':
        raw['checks'][2].update(status='FAIL', detail_code='declared_source_outside_prepared_set')
    elif damage == 'unrequested':
        raw['requested'] = False
    elif damage == 'detail':
        raw['checks'][0]['detail_code'] = 'symbol_and_numeric_declarations_consistent'
    elif damage == 'verdict':
        raw['mathematical'] = 'APPROVED'
    else:
        raw['checks'][0]['detail_code'] = 'private-prose-must-not-be-in-validation-error'
    with pytest.raises(ValidationError) as caught:
        StructuralReviewReport.model_validate(raw)
    assert 'private-prose-must-not-be-in-validation-error' not in str(caught.value)


def test_report_and_nested_checks_have_safe_repr(actual_material):
    _, material = actual_material
    result = review_structure(material, requested=True)
    assert repr(result) == 'StructuralReviewReport()'
    assert all(repr(check) == 'StructuralReviewCheck()' for check in result.checks)
    with pytest.raises(ApiError) as caught:
        review_structure(material, requested=1)
    assert caught.value.code == 'SCHEMA_INVALID'
