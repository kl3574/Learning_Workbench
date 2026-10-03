"""Existing real HTTP edit/review/publish routes and exact Reader readback; no browser claim."""

import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from tests.integration.test_review_http import prepared_review_http as prepared_review_http
from tests.integration.test_draft_edit_http import published_base
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def ready(case):
    base = published_base(case)
    created = case.client.post(
        "/api/v1/drafts",
        json={"kind": "block", "base_ref": base.model_dump(mode="json"), "title": "Synthetic revised publication"},
        headers=command(case.headers, "create"),
    )
    assert created.status_code == 201, created.text
    identifier = created.json()["draft_id"]
    text = "精确修订文本 🌏\nSynthetic revised prose.\n"
    patched = case.client.patch(
        f"/api/v1/drafts/{identifier}",
        json={"expected_revision": 1, "patches": [{"field": "body_markdown", "value": text}]},
        headers=command(case.headers, "patch"),
    )
    assert patched.status_code == 200, patched.text
    review = case.client.post(
        f"/api/v1/drafts/{identifier}/review",
        json={
            "expected_revision": 2,
            "checks": ["structure", "mathematics", "sources"],
            "reviewer_note": "Synthetic publication protocol only.",
        },
        headers=command(case.headers, "review-edit"),
    )
    assert review.status_code == 202, review.text
    assert case.app.state.review_worker.run_once()
    path = "/api/v1/reviews/" + review.json()["id"]
    machine = case.client.get(path).json()
    assert machine["mathematical"] == machine["sources"] == machine["independent_pedagogy"] == "NOT_RUN"
    human = case.client.post(
        path + "/decision",
        json={
            "expected_revision": machine["revision"],
            "candidate_sha256": machine["candidate"]["candidate_sha256"],
            "mathematical": "NOT_APPLICABLE",
            "sources": "APPROVED",
            "reason": "Synthetic protocol fixture, not real academic approval.",
            "evidence_artifact_ids": [],
        },
        headers=command(case.headers, "human-edit"),
    )
    assert human.status_code == 200, human.text
    body = {
        "expected_revision": 2,
        "expected_content_sha256": machine["candidate"]["candidate_sha256"],
        "review_receipt_id": review.json()["id"],
        "acknowledged_warning_codes": sorted(
            {w["code"] for w in patched.json()["validation_warnings"] if w["severity"] == "warning"}
        ),
    }
    return base, identifier, text, body


def test_real_http_edit_publish_exact_body_etags_and_original_ack(prepared_review_http):
    case = prepared_review_http
    base, identifier, text, body = ready(case)
    original = case.client.get(f"/api/v1/blocks/{base.id}/body?revision=1")
    path = f"/api/v1/drafts/{identifier}/publish"
    result = case.client.post(path, json=body, headers=command(case.headers, "publish-edit"))
    assert result.status_code == 201, result.text
    ref = dm.ContentRef.model_validate_json(result.content)
    assert ref.id == base.id and ref.revision == 2 and result.headers["cache-control"] == "no-store"
    metadata = case.client.get(f"/api/v1/blocks/{ref.id}?revision=2&include_provenance=true")
    assert metadata.status_code == 200, metadata.text
    assert metadata.headers["etag"] == '"' + ref.sha256 + '"'
    assert metadata.json()["block_ref"] == ref.model_dump(mode="json")
    assert metadata.json()["original_source"] is None
    assert {w["code"] for w in metadata.json()["warnings"]} == {"PROVENANCE_UNRESOLVED"}
    actual = case.client.get(f"/api/v1/blocks/{ref.id}/body?revision=2")
    assert actual.status_code == 200 and actual.content == text.encode("utf-8")
    assert actual.headers["etag"] == '"' + sha256_bytes(text.encode("utf-8")) + '"'
    assert case.client.get(f"/api/v1/blocks/{base.id}/body?revision=1").content == original.content
    assert case.client.get(f"/api/v1/drafts/{identifier}").status_code == 404  # No invented public editing GET.
    before = table_hashes(case.database)
    replay = case.client.post(path, json=body, headers=command(case.headers, "publish-edit"))
    assert replay.status_code == 201 and replay.content == result.content
    assert table_hashes(case.database) == before


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("missing_key", 400),
        ("duplicate_key", 400),
        ("csrf", 403),
        ("extra", 422),
        ("wrong_hash", 412),
        ("warnings", 409),
    ],
)
def test_existing_publish_transport_and_admission_fail_without_mutation(prepared_review_http, fault, expected):
    case = prepared_review_http
    _, identifier, _, body = ready(case)
    headers = command(case.headers, "publish-guard")
    if fault == "missing_key":
        headers.pop("Idempotency-Key")
    elif fault == "csrf":
        headers["X-CSRF-Token"] = "invalid-synthetic"
    elif fault == "extra":
        body["claimed_approval"] = True
    elif fault == "wrong_hash":
        body["expected_content_sha256"] = "0" * 64
    elif fault == "warnings":
        body["acknowledged_warning_codes"] = []
    values = list(headers.items())
    if fault == "duplicate_key":
        values.append(("Idempotency-Key", "another"))
    before = table_hashes(case.database)
    response = case.client.post(f"/api/v1/drafts/{identifier}/publish", json=body, headers=values)
    assert response.status_code == expected, response.text
    assert table_hashes(case.database) == before
