"""Actual six group HTTP operations and shared Job routing over real SQLite.

Only the explicit test loopback endpoint receives synthetic generation input.
Numeric previews are real frozen runtime reads; these HTTP cases never launch a
calculator and never claim draft review, publication, or vendor quality.
"""

import asyncio

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.content import ContentService
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code, expires_after
from services.api.app.provider_dto import ProviderConfigWrite, ProviderSecretWrite
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import import_fixture
from tests.integration.test_authoring_context import request as single_request
from tests.integration.test_authoring_group_context import request as lesson_request
from tests.integration.test_authoring_group_numeric_service import question_material
from tests.integration.test_authoring_http import command, session
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import MODEL, local_provider, test_preparer


def configure(identity, app, server):
    app.state.provider_service.secret_store.initialize()
    app.state.provider_service.save_config(
        identity,
        "test_provider",
        ProviderConfigWrite(
            expected_revision=0,
            adapter="compatible_chat",
            base_url=server.base_url,
            model=MODEL,
            embedding_model=None,
            endpoint_policy="explicit_loopback",
            pricing=None,
        ),
        "config",
    )
    app.state.provider_service.save_secret(
        identity, "test_provider", ProviderSecretWrite(expected_revision=1, secret="synthetic-group-http-key"), "secret"
    )


def grant(client, headers, identifier):
    preview = client.post(
        "/api/v1/consents/preview",
        json={
            "job_id": identifier,
            "expected_job_revision": 1,
            "provider_id": "test_provider",
            "expected_provider_revision": 2,
            "expires_at": expires_after(300),
            "budget": {
                "max_input_tokens": 20000,
                "max_output_tokens": 10000,
                "max_provider_calls": 1,
                "max_search_calls": 0,
                "max_tool_calls": 0,
                "timeout_seconds": 10,
                "max_cost_usd": None,
            },
        },
        headers=command(headers, "consent-preview"),
    )
    assert preview.status_code == 201, preview.text
    consent = client.post(
        "/api/v1/consents",
        json={"proposal_id": preview.json()["id"], "proposal_sha256": preview.json()["proposal_sha256"]},
        headers=command(headers, "consent-grant"),
    )
    assert consent.status_code == 201, consent.text


def safe_control(response):
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["result_refs"] == value["warnings"] == [] and value["error"] is None
    for private in ("raw_answer", "raw_refusal", "content_plan", "accepted_answers", "candidate_sha256"):
        assert private not in response.text
    return value


def test_unapproved_group_and_original_single_share_closed_get_and_safe_generic_cancel(tmp_path):
    async def run():
        async with local_provider(text="synthetic endpoint must receive no request") as server:
            database, identity, app, client, headers = session(tmp_path, test_preparer(server.base_url))
            try:
                configure(identity, app, server)
                body = lesson_request().model_dump(mode="json")
                before = all_rows(database)
                invalid = client.post(
                    "/api/v1/authoring/group-jobs",
                    json={**body, "draft_id": "invented"},
                    headers=command(headers, "bad-extra"),
                )
                assert invalid.status_code == 422 and all_rows(database) == before
                group = client.post("/api/v1/authoring/group-jobs", json=body, headers=command(headers, "group"))
                single = client.post(
                    "/api/v1/authoring/jobs",
                    json=single_request().model_dump(mode="json"),
                    headers=command(headers, "single"),
                )
                assert group.status_code == single.status_code == 202
                identifiers = [group.json()["id"], single.json()["id"]]
                before = all_rows(database)
                grouped = client.get("/api/v1/authoring/jobs/" + identifiers[0])
                original = client.get("/api/v1/authoring/jobs/" + identifiers[1])
                assert grouped.status_code == original.status_code == 200
                assert grouped.json()["variant"] == "group" and "variant" not in original.json()
                assert "root" not in grouped.json() and "root" not in original.json()
                assert grouped.json()["summary"]["status"] == "awaiting_approval"
                assert grouped.json()["plan_ref"] is grouped.json()["content_plan"] is None
                assert all_rows(database) == before
                schema = app.openapi()
                reply = schema["paths"]["/api/v1/authoring/jobs/{id}"]["get"]["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]
                assert reply == {"$ref": "#/components/schemas/AuthoringJobReadView"}
                union = schema["components"]["schemas"]["AuthoringJobReadView"]["anyOf"]
                assert len(union) == 2
                assert all(
                    schema["components"]["schemas"][branch["$ref"].split("/")[-1]]["additionalProperties"] is False
                    for branch in union
                )
                assert not app.state.authoring_worker.run_once()
                assert not app.state.authoring_group_worker.run_once()
                assert not app.state.group_numeric_worker.run_once()
                assert server.requests == []
                assert client.get("/api/v1/authoring/jobs/" + identifiers[0] + "?unexpected=1").status_code == 422
                switched = client.post(
                    "/api/v1/session/role", json={"role": "learner"}, headers=command(headers, "learner")
                )
                assert switched.status_code == 200
                for identifier in identifiers:
                    assert client.get("/api/v1/authoring/jobs/" + identifier).status_code == 403
                    safe_control(client.get("/api/v1/jobs/" + identifier))
                    cancelled = client.post(
                        "/api/v1/jobs/" + identifier + "/cancel",
                        json={"expected_revision": 1},
                        headers=command(headers, "cancel-" + identifier),
                    )
                    assert safe_control(cancelled)["status"] == "cancelled"
                    assert (
                        client.post(
                            "/api/v1/jobs/" + identifier + "/cancel",
                            json={"expected_revision": 1},
                            headers=command(headers, "cancel-" + identifier),
                        ).json()
                        == cancelled.json()
                    )
                assert server.requests == []
                with database.connect() as conn:
                    assert conn.execute("SELECT COUNT(*) FROM consents").fetchone()[0] == 0
                    assert conn.execute("SELECT COUNT(*) FROM authoring_group_candidates").fetchone()[0] == 0
            finally:
                client.close()

    asyncio.run(run())


@pytest.mark.parametrize("kind", ["practice_set", "assessment"])
def test_group_private_answers_numeric_routes_and_revocation_use_current_identity(tmp_path, kind):
    async def run():
        request, output, objects, bodies = question_material(kind)
        async with local_provider(text=canonical_bytes(output).decode()) as server:
            database, identity, app, client, headers = session(tmp_path, test_preparer(server.base_url))
            try:
                configure(identity, app, server)
                ContentService(database).publish(identity.workspace_id, objects, bodies)
                original = client.post(
                    "/api/v1/authoring/group-jobs",
                    json=request.model_dump(mode="json"),
                    headers=command(headers, "group-prepare"),
                )
                assert original.status_code == 202, original.text
                job_id = original.json()["id"]
                assert not app.state.authoring_group_worker.run_once() and server.requests == []
                grant(client, headers, job_id)
                assert not app.state.authoring_worker.run_once()
                assert await asyncio.to_thread(app.state.authoring_group_worker.run_once)
                current = client.get("/api/v1/authoring/jobs/" + job_id)
                assert current.status_code == 200, current.text
                assert current.json()["summary"]["status"] == "completed"
                candidate = current.json()["summary"]["candidate"]
                path = "/api/v1/authoring/draft-groups/" + candidate["draft_id"]
                before = all_rows(database)
                draft = client.get(path)
                assert draft.status_code == 200, draft.text
                public = draft.json()
                assert public["candidate"] == candidate and public["state"] == "draft" and public["base_ref"] is None
                assert "accepted_answers" not in draft.text and "仅私解" not in draft.text
                target = public["root"]["questions"][0]
                solution_path = path + "/solutions/" + target["member_key"]
                private = client.get(solution_path)
                assert private.status_code == 200, private.text
                for response in (current, draft, private):
                    assert response.headers["Cache-Control"] == "no-store"
                    assert response.headers["Vary"] == "Cookie"
                assert private.json()["payload"]["answer"]["accepted_answers"] == ["42", "42.0"]
                assert private.json()["payload"]["review_status"] == "needs_review"
                assert all_rows(database) == before
                assert client.get("/api/v1/authoring/drafts/" + candidate["draft_id"]).status_code == 404
                assert client.get("/api/v1/drafts/" + candidate["draft_id"]).status_code == 404
                assert client.get(solution_path + "?revision=1").status_code == 422
                numeric_path = path + "/members/" + target["member_key"] + "/numeric-checks"
                numeric_body = {"candidate": candidate, "target": target}
                first = client.post(
                    numeric_path, json=numeric_body, headers=command(headers, "numeric-decline-preview")
                )
                assert first.status_code == 201, first.text
                assert first.json()["job"] is first.json()["result"] is None
                check_path = "/api/v1/authoring/group-numeric-checks/" + first.json()["id"]
                decline_body = {
                    "expected_revision": 1,
                    "operation_sha256": first.json()["operation_sha256"],
                    "decision": "decline",
                }
                declined = client.post(check_path + "/decision", json=decline_body, headers=command(headers, "decline"))
                assert declined.status_code == 200 and declined.json()["job"] is None
                assert client.get(check_path).json()["decision"] == "decline"
                second = client.post(
                    numeric_path, json=numeric_body, headers=command(headers, "numeric-approve-preview")
                )
                assert second.status_code == 201, second.text
                selected_path = "/api/v1/authoring/group-numeric-checks/" + second.json()["id"]
                approval_body = {
                    "expected_revision": 1,
                    "operation_sha256": second.json()["operation_sha256"],
                    "decision": "approve_once",
                }
                approved = client.post(
                    selected_path + "/decision", json=approval_body, headers=command(headers, "approve")
                )
                assert approved.status_code == 202, approved.text
                numeric_id = approved.json()["job"]["id"]
                assert numeric_id != job_id and not app.state.numeric_worker.run_once()
                assert safe_control(client.get("/api/v1/jobs/" + numeric_id))["status"] == "queued"
                switch = client.post(
                    "/api/v1/session/role", json={"role": "learner"}, headers=command(headers, "demote")
                )
                assert switch.status_code == 200
                protected_paths = [path, solution_path, selected_path, "/api/v1/authoring/jobs/" + job_id]
                before = all_rows(database)
                for protected in protected_paths:
                    denied = client.get(protected)
                    assert denied.status_code == 403 and "仅私解" not in denied.text
                assert all_rows(database) == before
                cancelled = client.post(
                    "/api/v1/jobs/" + numeric_id + "/cancel",
                    json={"expected_revision": 1},
                    headers=command(headers, "numeric-cancel"),
                )
                assert safe_control(cancelled)["status"] == "cancelled"
                assert not app.state.group_numeric_worker.run_once()
                restored = client.post(
                    "/api/v1/session/role", json={"role": "author"}, headers=command(headers, "restore")
                )
                assert restored.status_code == 200
                result = client.get(selected_path)
                assert result.headers["Cache-Control"] == "no-store"
                assert result.headers["Vary"] == "Cookie"
                assert result.json()["result"]["outcome"] == "cancelled"
                assert result.json()["result"]["started_at"] is None
                assert (
                    client.post(
                        selected_path + "/decision", json=approval_body, headers=command(headers, "approve")
                    ).json()
                    == approved.json()
                )
                assert client.get(path).json()["candidate"] == candidate
                assert client.get("/api/v1/authoring/jobs/" + job_id).json() == current.json()
                if kind == "practice_set":
                    # A different real learner starts independent work; the existing
                    # author cookie must immediately lose all subject-private reads.
                    fixture = assessment_fixture("grouphttppolicy")
                    import_fixture(database, identity, fixture, "http-policy-source")
                    _, learner = consume_bootstrap(database, issue_bootstrap_code(database))
                    attempt = AssessmentService(database).create_attempt(
                        learner,
                        fixture.assessment.id,
                        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode="independent"),
                        "independent",
                    )
                    assert attempt.status == "active"
                    before = all_rows(database)
                    for protected in protected_paths:
                        denied = client.get(protected)
                        assert denied.status_code == 409 and "仅私解" not in denied.text
                    assert all_rows(database) == before
                    safe_control(client.get("/api/v1/jobs/" + numeric_id))
                # Retain the original cookie after the real logout mutation to prove
                # server revocation, rather than mere client cookie deletion.
                token = client.cookies.get(COOKIE_NAME)
                logout = client.post("/api/v1/session/logout", json={}, headers=headers)
                assert logout.status_code == 200
                client.cookies.set(COOKIE_NAME, token)
                before = all_rows(database)
                assert client.get(solution_path).status_code == 401
                assert all_rows(database) == before
                assert len(server.requests) == 1
            finally:
                client.close()

    asyncio.run(run())
