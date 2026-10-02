"""Actual collection endpoint and strict approved summary semantics."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from services.api.app.content_impact_dto import ContentImpactPage, ContentImpactSummary
from services.api.app.main import create_app


def summary():
    return dict(event_id='outbox_synthetic', old_ref=dict(entity='block', id='block_synthetic', revision=1, sha256='a'*64),
        new_ref=dict(entity='block', id='block_synthetic', revision=2, sha256='b'*64), reason='content_revision_published',
        evidence_version='owner_frozen_v1', event_snapshot_sha256='c'*64,
        pending_target_ids=['lesson_a', 'lesson_b'], action_required_target_ids=['course_a'])


def test_collection_registered_to_required_closed_page_and_query_models():
    api = create_app().openapi()
    operation = api['paths']['/api/v1/content/impacts']['get']
    assert operation['responses']['200']['content']['application/json']['schema'] == {'$ref':'#/components/schemas/ContentImpactPage'}
    assert {p['name'] for p in operation['parameters']} == {'changed_object_id', 'cursor', 'limit'}
    assert 'requestBody' not in operation
    for name in ['ContentImpactPage','ContentImpactSummary']:
        model = api['components']['schemas'][name]
        assert model['additionalProperties'] is False and set(model['required']) == set(model['properties'])
    assert api['components']['schemas']['ContentImpactPage']['properties']['items']['maxItems'] == 100
    assert ContentImpactPage(items=[ContentImpactSummary.model_validate(summary())], next_cursor=None).items[0].old_ref.revision == 1


@pytest.mark.parametrize('change', ['extra','missing_null','wrong_kind','wrong_entity','wrong_id','reverse_revision',
    'no_sha','legacy_sha','pending_duplicate','pending_unsorted','action_duplicate','overlap','bool_revision'])
def test_corrupt_summary_rejected(change):
    value = deepcopy(summary())
    if change == 'extra': value['reason_text'] = 'not public'
    elif change == 'missing_null': value.pop('event_snapshot_sha256')
    elif change == 'wrong_kind': value['old_ref']['entity'] = value['new_ref']['entity'] = 'note'
    elif change == 'wrong_entity': value['new_ref']['entity'] = 'lesson'
    elif change == 'wrong_id': value['new_ref']['id'] = 'other'
    elif change == 'reverse_revision': value['new_ref']['revision'] = 1
    elif change == 'no_sha': value['event_snapshot_sha256'] = None
    elif change == 'legacy_sha': value['evidence_version'] = 'legacy_unverified'
    elif change == 'pending_duplicate': value['pending_target_ids'] = ['lesson_a','lesson_a']
    elif change == 'pending_unsorted': value['pending_target_ids'].reverse()
    elif change == 'action_duplicate': value['action_required_target_ids'] = ['course_a','course_a']
    elif change == 'overlap': value['action_required_target_ids'] = ['lesson_a']
    elif change == 'bool_revision': value['old_ref']['revision'] = True
    with pytest.raises(ValidationError): ContentImpactSummary.model_validate(value)


@pytest.mark.parametrize('value', [dict(items=[summary(),summary()], next_cursor=None),
    dict(items=[],next_cursor=''), dict(items=[]), dict(items=[],next_cursor=None,secret='not public')])
def test_page_cannot_duplicate_events_or_relax_nullable_contract(value):
    with pytest.raises(ValidationError): ContentImpactPage.model_validate(value)
