"""A new Codex wrapper must not expand the old Tutor route adapter."""
from copy import deepcopy
from pathlib import Path

import pytest

from packages.contracts.spec_catalog import route_catalog, spec_metadata
from scripts.api_contracts import api_artifacts
from services.api.app.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def generate(api):
    return api_artifacts(api, route_catalog(ROOT / 'PRODUCT_DESIGN.md'), spec_metadata(ROOT / 'PRODUCT_DESIGN.md'))


def test_tutor_route_rejects_misbound_codex_wrapper():
    api = create_app().openapi()
    tutor = api['paths']['/api/v1/runs/{id}/events']['get']['responses']['200']['content']['text/event-stream']
    codex = api['paths']['/api/v1/codex/turns/{id}/events']['get']['responses']['200']['content']['text/event-stream']
    tutor['schema'] = deepcopy(codex['schema'])
    with pytest.raises(ValueError, match='Tutor SSE'):
        generate(api)


def test_codex_wrapper_cannot_be_a_string_with_object_fields():
    api = create_app().openapi()
    api['components']['schemas']['CodexTurnEvent']['type'] = 'string'
    with pytest.raises(ValueError, match='Codex SSE'):
        generate(api)
