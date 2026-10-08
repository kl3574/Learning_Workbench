"""The new application port binds registered DTOs without widening the core map."""

from copy import deepcopy
from pathlib import Path
import subprocess

import pytest

from packages.contracts import domain_models as dm
from scripts.generate_contracts import recommendation_ports_binding
from scripts.schema_types import generate_types
from services.api.app.recommendation_dto import RecommendationDecisionWrite, RecommendationPage

ROOT = Path(__file__).resolve().parents[2]
PROVENANCE = {'source': 'PRODUCT_DESIGN.md', 'spec_version': '3.0.1', 'spec_sha256': 'a' * 64}
PORTS = (ROOT / 'packages/contracts/module-ports.ts').read_text()


def shape_openapi() -> dict:
    """Synthetic generator input, not registration/acceptance evidence for product routes."""
    def schema(name):
        return {'application/json': {'schema': {'$ref': f'#/components/schemas/{name}'}}}

    return {'paths': {
        '/api/v1/recommendations': {'get': {'responses': {'200': {'content': schema('RecommendationPage')}}}},
        '/api/v1/recommendations/{id}/decision': {'post': {
            'requestBody': {'content': schema('RecommendationDecisionWrite')},
            'responses': {'200': {'content': schema('MutationAck')}},
        }},
    }, 'components': {'schemas': {
        model.__name__: model.model_json_schema()
        for model in (RecommendationPage, RecommendationDecisionWrite, dm.MutationAck)
    }}}


def test_missing_real_route_cannot_be_replaced_by_a_schema_only():
    value = shape_openapi()
    value['paths'] = {}
    with pytest.raises(ValueError, match='both registered runtime operations'):
        recommendation_ports_binding(PORTS, value, PROVENANCE)
    value = shape_openapi()
    del value['paths']['/api/v1/recommendations/{id}/decision']
    with pytest.raises(ValueError, match='both registered runtime operations'):
        recommendation_ports_binding(PORTS, value, PROVENANCE)


@pytest.mark.parametrize('bad', ['Recommendation', 'object', 'MissingApplicationDTO'])
def test_wrong_response_model_never_silently_binds_core_or_unknown(bad):
    value = shape_openapi()
    value['paths']['/api/v1/recommendations']['get']['responses']['200']['content']['application/json']['schema'] = {
        '$ref': f'#/components/schemas/{bad}'}
    with pytest.raises(ValueError, match='runtime response'):
        recommendation_ports_binding(PORTS, value, PROVENANCE)


def test_wrong_request_or_nonclosed_model_is_rejected():
    value = shape_openapi()
    value['paths']['/api/v1/recommendations/{id}/decision']['post']['requestBody']['content']['application/json']['schema'] = {'type': 'object'}
    with pytest.raises(ValueError, match='runtime request'):
        recommendation_ports_binding(PORTS, value, PROVENANCE)
    for name in ['RecommendationPage', 'RecommendationDecisionWrite', 'MutationAck']:
        value = shape_openapi()
        value['components']['schemas'][name]['additionalProperties'] = True
        with pytest.raises(ValueError, match='registered closed object'):
            recommendation_ports_binding(PORTS, value, PROVENANCE)


def test_unmapped_or_duplicate_generic_fields_fail_closed():
    for edited in [PORTS.replace(' RecommendationPage: unknown;', ' Recommendation: unknown;'),
                   PORTS.replace(' RecommendationPage: unknown;', ' RecommendationPage: unknown; RecommendationPage: unknown;'),
                   PORTS.replace(' RecommendationPage: unknown;', ' RecommendationPage: unknown; Other: any;')]:
        with pytest.raises(ValueError, match='unmapped or duplicate'):
            recommendation_ports_binding(edited, shape_openapi(), PROVENANCE)


def test_core_map_does_not_inherit_application_dto_names():
    block = PORTS.split('export interface DTOMap {', 1)[1].split('}', 1)[0]
    assert 'RecommendationPage' not in block
    assert 'RecommendationDecisionWrite' not in block
    assert "recommendations(ctx:AuthContext):Promise<D['Recommendation'][]>" not in PORTS
    output = recommendation_ports_binding(PORTS, shape_openapi(), PROVENANCE)
    assert 'RecommendationApplicationDTOMap extends RecommendationDTOMap' in output
    assert 'Api.RecommendationPage' in output
    assert 'Model.Recommendation' not in output


def test_emitted_application_binding_and_nested_types_compile_with_no_unknown_escape(tmp_path):
    generated = tmp_path / 'generated'
    generated.mkdir()
    (tmp_path / 'module-ports.ts').write_text(PORTS)
    value = shape_openapi()
    binding = recommendation_ports_binding(PORTS, value, PROVENANCE)
    (generated / 'recommendation-ports-binding.ts').write_text(binding)
    (generated / 'api-types.ts').write_text(generate_types(deepcopy(value['components']['schemas']), PROVENANCE))
    (tmp_path / 'verify.ts').write_text('''import type { RecommendationPort } from './module-ports';
import type { RecommendationApplicationDTOMap } from './generated/recommendation-ports-binding';
import type { RecommendationDecisionWrite, RecommendationPage } from './generated/api-types';
declare const port: RecommendationPort<RecommendationApplicationDTOMap>;
type IsUnknown<T> = unknown extends T ? true : false;
const resultIsKnown: IsUnknown<Awaited<ReturnType<typeof port.read>>> = false;
const pending: RecommendationDecisionWrite = { decision: 'accepted', reason: null };
// @ts-expect-error nullable reason is required
const missingReason: RecommendationDecisionWrite = { decision: 'dismissed' };
// @ts-expect-error pending is not a user decision
const wrongDecision: RecommendationDecisionWrite = { decision: 'pending', reason: null };
declare const page: RecommendationPage;
const exactHash: string = page.items[0].target_ref.sha256;
const reply: 'missing' | 'pending_refresh' | 'ready' | 'stale' | 'failed' = page.projection_state;
// @ts-expect-error the old undocumented alias is absent
const wrongAlias = page.items[0].target;
// @ts-expect-error ContentRef cannot masquerade as an Evidence reference
const wrongEvidence: RecommendationPage['items'][number]['evidence_refs'][number] = page.items[0].target_ref;
''')
    result = subprocess.run(['bash', str(ROOT / 'scripts/node.sh'),
        str(ROOT / 'apps/web/node_modules/.bin/tsc'), '--strict', '--skipLibCheck', '--noEmit',
        '--target', 'ES2022', '--module', 'ESNext', '--moduleResolution', 'Bundler', '--lib', 'ES2022,DOM',
        'verify.ts', 'module-ports.ts', 'generated/api-types.ts', 'generated/recommendation-ports-binding.ts'],
        cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
