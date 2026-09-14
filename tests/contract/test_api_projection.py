"""Coverage checks actual registered handlers, never registers future API stubs."""
import json
from pathlib import Path

from fastapi.routing import APIRoute, iter_route_contexts
from jsonschema import Draft202012Validator
import pytest

from packages.contracts.spec_catalog import route_catalog
from scripts.api_contracts import HTTP_METHODS
from services.api.app.config import Settings
from services.api.app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
SPEC_ROUTES = {(route["method"], route["path"]) for route in route_catalog(ROOT / "PRODUCT_DESIGN.md")["routes"]}


def test_app_factory_and_openapi_generation_have_no_storage_side_effect(tmp_path):
    target = tmp_path / "must-not-exist"
    application = create_app(Settings(data_dir=target))
    api = application.openapi()
    assert api["openapi"] == "3.1.0"
    assert not target.exists()


def test_router_and_openapi_are_bidirectionally_equal_and_subset_of_spec():
    application = create_app()
    api = application.openapi()
    runtime = {(method, context.path) for context in iter_route_contexts(application.routes)
               if isinstance(context.original_route, APIRoute) for method in context.methods}
    projection = {(method.upper(), path) for path, methods in api["paths"].items() for method in methods if method in HTTP_METHODS}
    assert runtime == projection
    assert projection <= SPEC_ROUTES
    assert len(projection) == 41
    assert len(SPEC_ROUTES - projection) == 61


OPERATIONS = [(path, method, operation) for path, methods in create_app().openapi()["paths"].items()
              for method, operation in methods.items() if method in HTTP_METHODS]


@pytest.mark.parametrize("path,method,operation", OPERATIONS, ids=[f"{method.upper()} {path}" for path, method, _ in OPERATIONS])
def test_implemented_route_is_in_spec_and_has_strict_openapi_contract(path, method, operation):
    assert (method.upper(), path) in SPEC_ROUTES
    api = create_app().openapi()
    for schema in api["components"]["schemas"].values():
        Draft202012Validator.check_schema(schema)
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
        else:
            # A named RootModel projects the two concrete block-read shapes.
            # Every union branch must still be a closed named object contract.
            assert schema["title"] == "BlockReadResponse"
            assert {"anyOf", "title"} <= set(schema) <= {"anyOf", "title", "description"}
            assert len(schema["anyOf"]) == 2
            for alternative in schema["anyOf"]:
                assert set(alternative) == {"$ref"}
                target = api["components"]["schemas"][alternative["$ref"].rsplit("/", 1)[1]]
                assert target["type"] == "object"
                assert target["additionalProperties"] is False
    for code, response in operation["responses"].items():
        if int(code) >= 400:
            assert response["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/ErrorEnvelope"
    if method == "delete":
        assert path == "/api/v1/notes/{id}"
        assert "requestBody" not in operation
        headers = {value["name"] for value in operation["parameters"] if value["in"] == "header"}
        assert {"If-Match", "Idempotency-Key"} <= headers
    elif method != "get":
        media = "multipart/form-data" if path == "/api/v1/imports" else "application/json"
        assert set(operation["requestBody"]["content"]) == {media}
        assert operation["requestBody"]["content"][media]["schema"]["$ref"]


def test_saved_openapi_matches_actual_registered_handlers_and_coverage():
    generated = json.loads((ROOT / "packages/contracts/generated/openapi.json").read_text())
    generated.pop("x-source-spec")
    assert generated == create_app().openapi()
    coverage = json.loads((ROOT / "packages/contracts/generated/runtime-route-coverage.json").read_text())
    declared = {f"{method} {path}" for method, path in SPEC_ROUTES}
    registered = set(coverage["registered_operations"])
    backlog = set(coverage["not_registered_operations"])
    assert not registered & backlog
    assert registered | backlog == declared
    assert coverage["product_acceptance"] == "NOT_RUN"
