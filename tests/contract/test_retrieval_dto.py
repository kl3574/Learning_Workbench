"""M5.2 public shape counterexamples; no source-authority or retrieval-quality claim."""

from pydantic import ValidationError
import pytest

from services.api.app import retrieval_dto as dto


def block_ref():
    return {'entity': 'block', 'id': 'block_contract', 'revision': 1, 'sha256': 'a' * 64}


def scope_status():
    return {
        'kind': 'scope', 'scope_sha256': 'b' * 64, 'scope_refs': [block_ref()],
        'corpus_sha256': 'c' * 64, 'state': 'missing', 'indexed_corpus_sha256': None,
        'index_version': None, 'last_built_at': None, 'latest_job': None,
    }


def test_building_scope_requires_an_actual_active_job_for_its_target():
    value = scope_status()
    value['state'] = 'building'
    with pytest.raises(ValidationError):
        dto.RetrievalIndexScopeStatus.model_validate(value)


@pytest.mark.parametrize('status,error', [
    ('failed', None),
    *[(status, {'code': 'CONTROLLED', 'message': '合成失败诊断', 'retryable': False})
      for status in ('queued', 'running', 'awaiting_approval', 'completed', 'cancelled')],
])
def test_job_summary_has_a_diagnostic_exactly_when_failed(status, error):
    with pytest.raises(ValidationError):
        dto.RetrievalJobSummary.model_validate({
            'job': {'id': 'job_contract', 'status': status},
            'target_corpus_sha256': 'c' * 64, 'error': error,
        })


def test_registered_scope_cannot_invent_registration_without_index_or_job():
    with pytest.raises(ValidationError):
        dto.RetrievalRegisteredScope.model_validate({
            'scope_sha256': 'b' * 64, 'scope_refs': [block_ref()],
            'latest_index': None, 'latest_job': None,
        })


def test_query_normalizes_full_refs_without_guessing_or_coercing():
    first = block_ref()
    second = {**first, 'id': 'block_second'}
    value = dto.RetrievalQueryWrite.model_validate({
        'query': '  概率 e\u0301 😀  ', 'scope_refs': [second, first, first], 'limit': 20})
    assert value.query == '  概率 e\u0301 😀  '
    assert [ref.id for ref in value.scope_refs] == ['block_contract', 'block_second']
    assert value.model_dump(mode='json')['scope_refs'][0] == first


@pytest.mark.parametrize('change', ['empty', 'blank', 'surrogate', 'long', 'missing_limit', 'bool_limit',
    'float_limit', 'string_limit', 'zero_limit', 'large_limit', 'roots_empty', 'roots_17', 'hash_conflict',
    'private_entity', 'missing_hash', 'unknown'])
def test_query_rejects_invalid_explicit_scope_and_scalar_boundaries(change):
    value = {'query': '概率', 'scope_refs': [block_ref()], 'limit': 10}
    if change in {'empty', 'blank', 'surrogate', 'long'}:
        value['query'] = {'empty': '', 'blank': ' \n', 'surrogate': '\ud800', 'long': '😀' * 513}[change]
    elif change == 'missing_limit':
        del value['limit']
    elif change.endswith('_limit'):
        value['limit'] = {'bool_limit': True, 'float_limit': 1.0, 'string_limit': '1',
                          'zero_limit': 0, 'large_limit': 21}[change]
    elif change == 'roots_empty':
        value['scope_refs'] = []
    elif change == 'roots_17':
        value['scope_refs'] = [block_ref()] * 17  # Input bound applies before deduplication.
    elif change == 'hash_conflict':
        value['scope_refs'] = [block_ref(), {**block_ref(), 'sha256': 'd' * 64}]
    elif change == 'private_entity':
        value['scope_refs'] = [{**block_ref(), 'entity': 'question'}]
    elif change == 'missing_hash':
        ref = block_ref()
        del ref['sha256']
        value['scope_refs'] = [ref]
    else:
        value['latest'] = True
    with pytest.raises(ValidationError):
        dto.RetrievalQueryWrite.model_validate(value)


def test_rebuild_nullable_remote_ids_are_required_and_legal_ids_reach_capability_check():
    body = {'scope_refs': [block_ref()], 'expected_corpus_sha256': 'c' * 64,
            'provider_id': None, 'consent_id': None}
    assert dto.RetrievalIndexRebuildWrite.model_validate(body).provider_id is None
    assert dto.RetrievalIndexRebuildWrite.model_validate({**body, 'provider_id': 'provider_local'}).provider_id
    for missing in ('scope_refs', 'expected_corpus_sha256', 'provider_id', 'consent_id'):
        with pytest.raises(ValidationError):
            dto.RetrievalIndexRebuildWrite.model_validate({key: value for key, value in body.items() if key != missing})


def test_ready_precedes_redundant_job_but_building_requires_current_nonterminal_target():
    job = {'job': {'id': 'job_contract', 'status': 'queued'}, 'target_corpus_sha256': 'c' * 64, 'error': None}
    building = {**scope_status(), 'state': 'building', 'latest_job': job}
    assert dto.RetrievalIndexScopeStatus.model_validate(building).state == 'building'
    ready = {**building, 'state': 'ready', 'indexed_corpus_sha256': 'c' * 64,
             'index_version': 'index_contract', 'last_built_at': '2026-09-15T00:00:00Z'}
    assert dto.RetrievalIndexScopeStatus.model_validate(ready).latest_job is not None
    for change in ({**job, 'target_corpus_sha256': 'd' * 64},
                   {**job, 'job': {'id': 'job_contract', 'status': 'completed'}}):
        with pytest.raises(ValidationError):
            dto.RetrievalIndexScopeStatus.model_validate({**building, 'latest_job': change})


def test_scope_status_generation_fields_are_required_even_when_null():
    for name in ('indexed_corpus_sha256', 'index_version', 'last_built_at', 'latest_job'):
        with pytest.raises(ValidationError):
            dto.RetrievalIndexScopeStatus.model_validate({key: value for key, value in scope_status().items() if key != name})
