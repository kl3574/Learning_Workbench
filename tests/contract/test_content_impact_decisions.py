"""v3.0.9 Content impact strict runtime route contracts, independent of 54 core."""
import pytest
from pydantic import ValidationError
from services.api.app.content_impact_dto import ContentImpactView, ImpactObjectDecisionReceipt, ImpactObjectDecisionWrite
from services.api.app.main import create_app


def test_actual_http_routes_bind_closed_required_application_models():
    schema = create_app().openapi()
    get = schema['paths']['/api/v1/content/impacts/{event_id}']['get']
    post = schema['paths']['/api/v1/content/impacts/{event_id}/decisions']['post']
    assert get['responses']['200']['content']['application/json']['schema'] == {'$ref':'#/components/schemas/ContentImpactView'}
    assert post['responses']['200']['content']['application/json']['schema'] == {'$ref':'#/components/schemas/ImpactObjectDecisionReceipt'}
    assert post['requestBody']['content']['application/json']['schema'] == {'$ref':'#/components/schemas/ImpactObjectDecisionWrite'}
    for name in ['ContentImpactView', 'ImpactObjectDecisionReceipt', 'ImpactObjectDecisionWrite', 'ImpactArtifact']:
        component = schema['components']['schemas'][name]
        assert component['additionalProperties'] is False
        assert set(component['required']) == set(component['properties'])
    assert any(p['name']=='Idempotency-Key' and p['required'] for p in post['parameters'])
    assert {p['name'] for p in get['parameters']} == {'event_id','target_id','cursor','limit'}


@pytest.mark.parametrize('model', [ContentImpactView, ImpactObjectDecisionReceipt, ImpactObjectDecisionWrite])
def test_models_reject_untrusted_partial_objects(model):
    with pytest.raises(ValidationError):
        model.model_validate({'forged_owner':'author'})
