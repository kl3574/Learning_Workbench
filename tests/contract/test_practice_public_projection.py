"""Public practice contracts exercised against actual imports and SQLite services."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest

from packages.contracts import domain_models as dm
from services.api.app import practice_dto as dto
from services.api.app.application.imports import ImportService
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.interfaces.boundary import install_boundary
from services.api.app.interfaces.http import create_router
from services.api.app.interfaces.import_http import create_import_router
from services.api.app.security import issue_bootstrap_code

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "synthetic"
OPERATIONS = {
    ("get", "/api/v1/practice/sets"),
    ("post", "/api/v1/practice/sessions"),
    ("get", "/api/v1/practice/sessions/{id}"),
    ("put", "/api/v1/practice/sessions/{id}/responses"),
    ("post", "/api/v1/practice/sessions/{id}/submit"),
    ("post", "/api/v1/practice/sessions/{id}/hints"),
    ("post", "/api/v1/practice/sessions/{id}/solutions"),
}
PRIVATE_FIELDS = {
    "accepted_answers", "absolute_tolerance", "relative_tolerance", "rubric_markdown", "domain_assumptions",
    "solution_refs", "solution_refs_json", "solution_refs_private_json", "solution_revision", "solution_sha256",
    "private_json", "rubric_private", "answer_key",
}
CONTRACTS = [dto.PagePracticeSet, dto.PracticeSetSummary, dto.PracticeSessionCreate, dto.PracticeAssistance,
             dto.PracticeSession, dto.PracticeSessionCreated, dto.PracticeResponsesSaved, dto.PracticeSubmitRequest,
             dto.PracticeSubmitted, dto.PracticeHintRequest, dto.PracticeHint, dto.PracticeSolutionRequest, dto.PracticeSolution]


def no_private_values(value):
    if isinstance(value, dict):
        assert not PRIVATE_FIELDS.intersection(value)
        if "solution_markdown" in value:
            assert value["solution_markdown"] is None
        for nested in value.values():
            no_private_values(nested)
    elif isinstance(value, list):
        for nested in value:
            no_private_values(nested)


@pytest.mark.parametrize("model", CONTRACTS)
def test_practice_contracts_are_closed_valid_schemas(model):
    schema = model.model_json_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    for definition in schema.get("$defs", {}).values():
        assert definition["additionalProperties"] is False


@pytest.mark.parametrize("level", [True, False, 1.0, "1", 0, 4, None])
def test_hint_request_rejects_non_integer_or_unavailable_levels(level):
    with pytest.raises(ValidationError):
        dto.PracticeHintRequest(question_id="question_synthetic", expected_revision=1, level=level)


def test_create_rejects_unknown_private_and_wrong_reference_fields():
    ref = {"entity": "practice_set", "id": "practice_synthetic", "revision": 1, "sha256": "a" * 64}
    dto.PracticeSessionCreate.model_validate({"practice_ref": ref})
    for candidate in [
        {"practice_ref": ref, "solution_refs": []},
        {"practice_ref": {**ref, "entity": "lesson"}},
        {"practice_ref": {**ref, "revision": True}},
        {"practice_ref": {**ref, "sha256": "latest"}},
    ]:
        with pytest.raises(ValidationError):
            dto.PracticeSessionCreate.model_validate(candidate)


@pytest.mark.parametrize("model", [dto.PracticeSession, dto.PracticeSessionCreated])
def test_session_requires_exact_typed_lesson_parent(model):
    question = dm.QuestionPublic(id="question_synthetic", revision=1, kind="numeric", stem_markdown="合成题",
        concept_ids=["concept_synthetic"], skill="compute", exposure_group="synthetic_parent", input_instructions="填写数值")
    value = {"id": "practice_session_synthetic", "revision": 1,
        "practice_ref": {"entity": "practice_set", "id": "practice_synthetic", "revision": 1, "sha256": "a" * 64},
        "lesson_ref": {"entity": "lesson", "id": "lesson_synthetic", "revision": 2, "sha256": "b" * 64},
        "questions": [question.model_dump(mode="json")], "responses": [], "status": "active", "exposure_event_ids": [],
        "assisted": False, "assistance": [{"question_id": question.id, "highest_hint_level": 0, "solution_revealed": False}], "results": None}
    assert model.model_validate(value).lesson_ref.revision == 2
    assert "lesson_ref" in model.model_json_schema()["required"]
    candidates = [{key: item for key, item in value.items() if key != "lesson_ref"}]
    candidates += [{**value, "lesson_ref": {**value["lesson_ref"], **change}} for change in (
        {"entity": "course"}, {"revision": True}, {"sha256": "current"}, {"unknown": "field"})]
    for candidate in candidates:
        with pytest.raises(ValidationError):
            model.model_validate(candidate)


@pytest.fixture
def practice_http(tmp_path):
    # Import here so DTO-only checks can run while the independently implemented
    # real application port is still being connected. No service is stubbed.
    from services.api.app.interfaces.practice_http import create_practice_router

    settings = Settings(data_dir=tmp_path / "data")
    database = Database(settings)
    database.initialize()
    worker = ImportWorker(database)
    app = FastAPI()
    install_boundary(app, settings, database)
    app.include_router(create_router(settings, database))
    app.include_router(create_import_router(settings, ImportService(database)))
    app.include_router(create_practice_router(database))
    with TestClient(app, base_url=settings.origin) as client:
        bootstrap = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)},
                                headers={"Origin": settings.origin})
        assert bootstrap.status_code == 200
        headers = {"Origin": settings.origin, "X-CSRF-Token": bootstrap.json()["csrf_token"], "Idempotency-Key": "author-role"}
        assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers).status_code == 200
        staged = client.post("/api/v1/imports", data={"kind": "learnpack"},
            files={"file": ("synthetic-author.learnpack.zip", (FIXTURES / "course-author.learnpack.zip").read_bytes(), "application/zip")},
            headers={**headers, "Idempotency-Key": "import-author"})
        assert staged.status_code == 202, staged.text
        assert worker.run_once()
        imported = client.get(f"/api/v1/imports/{staged.json()['import_id']}")
        assert imported.status_code == 200
        preview = imported.json()
        assert preview["status"] == "preview_ready", preview
        commit = client.post(f"/api/v1/imports/{staged.json()['import_id']}/commit", json={
            "expected_input_sha256": staged.json()["input_sha256"], "id_mapping": [],
            "accepted_warning_codes": sorted({item["code"] for item in preview["warnings"] if item["severity"] == "warning"}),
        }, headers={**headers, "Idempotency-Key": "commit-author"})
        assert commit.status_code == 200, commit.text
        assert client.post("/api/v1/session/role", json={"role": "learner"},
                           headers={**headers, "Idempotency-Key": "learner-role"}).status_code == 200
        try:
            yield client, headers, database, app
        finally:
            worker.stop()


def create_session(client, headers):
    listed = client.get("/api/v1/practice/sets")
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 1
    reference = listed.json()["items"][0]["ref"]
    response = client.post("/api/v1/practice/sessions", json={"practice_ref": reference},
                           headers={**headers, "Idempotency-Key": "create-practice"})
    assert response.status_code == 201, response.text
    return response.json()


def test_seven_actual_handlers_project_strict_openapi_without_private_solution_model(practice_http):
    _, _, _, app = practice_http
    api = app.openapi()
    operations = {(method, path) for path, methods in api["paths"].items() if path.startswith("/api/v1/practice/")
                  for method in methods if method in {"get", "post", "put", "patch", "delete"}}
    assert operations == OPERATIONS
    schemas = api["components"]["schemas"]
    assert "SolutionPrivate" not in schemas
    for name in [model.__name__ for model in CONTRACTS]:
        assert schemas[name]["additionalProperties"] is False
    for method, path in OPERATIONS:
        parameters = api["paths"][path][method].get("parameters", [])
        if method != "get":
            required_headers = {item["name"] for item in parameters if item["in"] == "header" and item["required"]}
            assert {"Origin", "X-CSRF-Token", "Idempotency-Key"} <= required_headers


def test_created_saved_submitted_and_restored_views_never_release_private_answer(practice_http):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    assert session["lesson_ref"] == client.get("/api/v1/practice/sets").json()["items"][0]["lesson_ref"]
    assert session["status"] == "active" and session["results"] is None
    assert not session["assisted"] and session["exposure_event_ids"] == []
    assert all(item["highest_hint_level"] == 0 and not item["solution_revealed"] for item in session["assistance"])
    no_private_values(session)
    response = client.put(f"/api/v1/practice/sessions/{session['id']}/responses", json={
        "expected_revision": session["revision"], "responses": [
            {"question_id": session["questions"][0]["id"], "answer": "opt_a", "steps_markdown": "合成用户思路"},
        ],
    }, headers={**headers, "Idempotency-Key": "save-practice"})
    assert response.status_code == 200, response.text
    restored = client.get(f"/api/v1/practice/sessions/{session['id']}")
    assert restored.status_code == 200
    assert restored.json()["responses"][0]["steps_markdown"] == "合成用户思路"
    submitted = client.post(f"/api/v1/practice/sessions/{session['id']}/submit",
        json={"expected_revision": response.json()["revision"]}, headers={**headers, "Idempotency-Key": "submit-practice"})
    assert submitted.status_code == 200, submitted.text
    value = submitted.json()
    assert value["evidence_label"] == "practice"
    assert all(item["status"] == "needs_review" and item["score"] is None and item["solution_markdown"] is None
               for item in value["results"])
    no_private_values(value)
    final = client.get(f"/api/v1/practice/sessions/{session['id']}")
    assert final.status_code == 200 and final.json()["results"] == value["results"]
    no_private_values(final.json())
    assert final.headers["cache-control"] == "no-store" and final.headers["vary"] == "Cookie"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM solutions WHERE review_status='needs_review'").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 0


def test_only_explicit_reveal_releases_unreviewed_solution_and_records_assistance(practice_http):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    question_id = session["questions"][0]["id"]
    hint = client.post(f"/api/v1/practice/sessions/{session['id']}/hints", json={
        "question_id": question_id, "expected_revision": session["revision"], "level": 2,
    }, headers={**headers, "Idempotency-Key": "reveal-hint"})
    assert hint.status_code == 200, hint.text
    assert hint.json()["source"] == "rules" and hint.json()["level"] == 2 and hint.json()["rule_version"]
    no_private_values(hint.json())
    reveal = client.post(f"/api/v1/practice/sessions/{session['id']}/solutions", json={
        "question_id": question_id, "expected_revision": hint.json()["revision"],
    }, headers={**headers, "Idempotency-Key": "reveal-solution"})
    assert reveal.status_code == 200, reveal.text
    dto.PracticeSolution.model_validate(reveal.json())
    assert reveal.json()["review_status"] == "needs_review"
    assert "此为合成测试材料" in reveal.json()["solution_markdown"]
    restored = client.get(f"/api/v1/practice/sessions/{session['id']}").json()
    no_private_values(restored)
    assert restored["assisted"]
    state = next(item for item in restored["assistance"] if item["question_id"] == question_id)
    assert state == {"question_id": question_id, "highest_hint_level": 2, "solution_revealed": True}
    assert {hint.json()["exposure_event_id"], reveal.json()["exposure_event_id"]} <= set(restored["exposure_event_ids"])
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM exposures WHERE kind IN ('hint','solution')").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM learning_events WHERE kind IN ('hint_revealed','solution_revealed')").fetchone()[0] == 2


@pytest.mark.parametrize("query", ["limit=1&limit=2", "course_id=course_ols&course_id=course_ols", "unexpected=private", "limit=101"])
def test_query_ambiguity_and_unknown_fields_are_rejected(practice_http, query):
    client, _, _, _ = practice_http
    assert client.get(f"/api/v1/practice/sets?{query}").status_code == 422


@pytest.mark.parametrize("header", ["Idempotency-Key", "X-CSRF-Token", "Content-Type"])
def test_repeated_write_headers_are_rejected_before_any_session_created(practice_http, header):
    client, headers, database, _ = practice_http
    reference = client.get("/api/v1/practice/sets").json()["items"][0]["ref"]
    repeated = list({**headers, "Content-Type": "application/json"}.items())
    repeated.append((header, dict(repeated)[header]))
    response = client.post("/api/v1/practice/sessions", json={"practice_ref": reference}, headers=repeated)
    assert response.status_code == 422, response.text
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM practice_sessions").fetchone()[0] == 0


def test_unknown_secret_fields_do_not_enter_echoes_or_session_storage(practice_http):
    client, headers, database, _ = practice_http
    reference = client.get("/api/v1/practice/sets").json()["items"][0]["ref"]
    response = client.post("/api/v1/practice/sessions", json={"practice_ref": reference, "accepted_answers": ["PRIVATE_SENTINEL_SYNTHETIC"]},
                           headers={**headers, "Idempotency-Key": "reject-private-input"})
    assert response.status_code == 422 and "PRIVATE_SENTINEL_SYNTHETIC" not in response.text
    dm.ErrorEnvelope.model_validate(response.json())
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM practice_sessions").fetchone()[0] == 0


def test_existing_learner_package_really_omits_private_payload_and_schema():
    from zipfile import ZipFile
    with ZipFile(FIXTURES / "course-learner.learnpack.zip") as archive:
        assert not any(name.startswith("private/") for name in archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert all(item["visibility"] == "learner" for item in manifest["files"])
        for line in archive.read("questions/public.jsonl").splitlines():
            no_private_values(dm.QuestionPublic.model_validate_json(line).model_dump(mode="json"))
