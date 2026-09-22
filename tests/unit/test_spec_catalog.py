from pathlib import Path

from packages.contracts.spec_catalog import route_catalog, traceability
from scripts.generate_contracts import generate
from scripts.schema_types import typescript_type
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_traceability_covers_all_stable_requirements_scenarios_tasks():
    catalog = traceability(ROOT / "PRODUCT_DESIGN.md")
    assert len(catalog["requirements"]) == 38
    assert len(catalog["scenarios"]) == 33
    assert len(catalog["tasks"]) == 27
    assert all(req["scenario_ids"] and req["task_ids"] for req in catalog["requirements"])
    assert all(scenario["execution_status"] == "NOT_RUN" for scenario in catalog["scenarios"])


def test_route_inventory_includes_inline_response_routes_and_e1():
    catalog = route_catalog(ROOT / "PRODUCT_DESIGN.md")
    routes = {(route["method"], route["path"]): route for route in catalog["routes"]}
    assert len(routes) == 113
    assert routes["GET", "/api/v1/authoring/drafts/{id}"]["task_id"] == "M6.1"
    assert routes["POST", "/api/v1/authoring/numeric-checks/{id}/decision"]["task_id"] == "M6.1"
    assert routes["GET", "/api/v1/blocks/{id}/body"]["location"] == "inline_response_cell"
    assert routes["GET", "/api/v1/attempts/{id}/responses"]["location"] == "inline_response_cell"
    assert routes["POST", "/api/v1/connectors/{id}/apply"]["priority"] == "P1"
    assert routes["GET", "/health"]["task_id"] == "M0.2"
    assert all("implementation_status" not in route for route in routes.values())
    assert all(route["runtime_evidence_source"] == "progress/state.json_and_runtime_openapi" for route in routes.values())


def test_generated_contracts_match_current_spec():
    assert generate(check=True) >= 59


def test_type_projection_fails_closed_for_unbounded_schema():
    with pytest.raises(ValueError, match="unbounded"):
        typescript_type({"type": "object", "additionalProperties": True})
    with pytest.raises(ValueError, match="unsupported"):
        typescript_type({})
