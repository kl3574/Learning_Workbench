"""A synthetic HTTP edit publication preserves learning history and dirties retrieval."""

import json

from packages.contracts import domain_models as dm
from services.api.app.application.grading import GradingWorker
from services.api.app.application.retrieval import RetrievalWorker
from services.api.app.infrastructure.content_repository import reference
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import import_fixture
from tests.integration.test_assessment_grading import review_request
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication_http import ready
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


_GRADE_HISTORY_TABLES = (
    "attempts", "grades", "assessment_grade_audits", "learning_grade_bindings",
    "evidence", "learning_evidence_refs",
)


def grade_history(database):
    with database.connect() as connection:
        return {
            table: tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid"))
            for table in _GRADE_HISTORY_TABLES
        }


def test_edit_publish_keeps_old_grade_marks_note_stale_and_invalidates_index(prepared_review_http):
    case = prepared_review_http
    base, identifier, revised_body, publish_body = ready(case)
    old_body = case.client.get(f"/api/v1/blocks/{base.id}/body?revision={base.revision}")
    assert old_body.status_code == 200

    # A real imported, unreviewed synthetic assessment first needs review. An
    # explicit synthetic human score resolves its independent-test protection;
    # neither decision approves the imported answer content.
    assessment = assessment_fixture("editgrade")
    import_fixture(case.database, case.identity, assessment, "edit-grade-import")
    start = case.client.post(
        f"/api/v1/assessments/{assessment.assessment.id}/attempts",
        json={"assessment_ref": reference(assessment.assessment).model_dump(mode="json"), "mode": "independent"},
        headers=command(case.headers, "edit-grade-start"),
    )
    assert start.status_code == 201, start.text
    attempt_id = start.json()["id"]
    submitted = case.client.post(
        f"/api/v1/attempts/{attempt_id}/submit", json={"expected_revision": start.json()["revision"]},
        headers=command(case.headers, "edit-grade-submit"),
    )
    assert submitted.status_code == 202, submitted.text
    assert GradingWorker(case.database).run_once()
    unreviewed_grade = case.client.get(f"/api/v1/attempts/{attempt_id}/result")
    assert unreviewed_grade.status_code == 200 and unreviewed_grade.json()["status"] == "needs_review"
    assert unreviewed_grade.json()["grading_revision"] == 1
    before_protected_publish = table_hashes(case.database)
    protected_publish = case.client.post(
        f"/api/v1/drafts/{identifier}/publish", json=publish_body,
        headers=command(case.headers, "edit-learn-protected"),
    )
    assert protected_publish.status_code == 409
    assert protected_publish.json()["error"]["code"] == "ASSESSMENT_ANSWER_PROTECTED"
    assert table_hashes(case.database) == before_protected_publish
    review = case.client.post(
        f"/api/v1/attempts/{attempt_id}/regrade",
        json=review_request(assessment).model_dump(mode="json"),
        headers=command(case.headers, "edit-grade-human-review"),
    )
    assert review.status_code == 202, review.text
    assert GradingWorker(case.database).run_once()
    old_grade = case.client.get(f"/api/v1/attempts/{attempt_id}/result")
    assert old_grade.status_code == 200 and old_grade.json()["status"] == "graded"
    assert old_grade.json()["grading_revision"] == 2
    assert all(item["score"] == item["max_score"] * 0.5 for item in old_grade.json()["items"])

    quote = "Synthetic"
    text = old_body.content.decode("utf-8")
    start_cp = text.index(quote)
    note = dm.Note(
        id="note_edit_publication", revision=1, workspace_id=case.identity.workspace_id,
        markdown="Old revision synthetic note.",
        anchor=dm.Selection(ref=base, exact_quote=quote, start_codepoint=start_cp,
                            end_codepoint=start_cp + len(quote)),
    )
    created_note = case.client.post("/api/v1/notes", json=note.model_dump(mode="json"),
                                    headers=command(case.headers, "edit-note-create"))
    assert created_note.status_code == 201, created_note.text

    scope_refs = [base.model_dump(mode="json")]
    status_path = "/api/v1/index/status"
    status_params = {"scope_refs": json.dumps(scope_refs)}
    cold = case.client.get(status_path, params=status_params)
    assert cold.status_code == 200 and cold.json()["state"] == "missing"
    rebuild = case.client.post(
        "/api/v1/index/rebuild",
        json={"scope_refs": scope_refs, "expected_corpus_sha256": cold.json()["corpus_sha256"],
              "provider_id": None, "consent_id": None},
        headers=command(case.headers, "edit-index-build"),
    )
    assert rebuild.status_code == 202, rebuild.text
    assert RetrievalWorker(case.database).run_once()
    ready_index = case.client.get(status_path, params=status_params)
    assert ready_index.status_code == 200 and ready_index.json()["state"] == "ready"
    query = {"query": quote, "scope_refs": scope_refs, "limit": 10}
    previous_hits = case.client.post("/api/v1/retrieval/query", json=query, headers=case.headers)
    assert previous_hits.status_code == 200 and previous_hits.json()["result_state"] == "matched"
    assert previous_hits.json()["hits"][0]["ref"] == scope_refs[0]

    frozen_grade_tables = grade_history(case.database)
    publication = case.client.post(
        f"/api/v1/drafts/{identifier}/publish", json=publish_body,
        headers=command(case.headers, "edit-learn-publish"),
    )
    assert publication.status_code == 201, publication.text
    new_ref = dm.ContentRef.model_validate_json(publication.content)
    assert new_ref.id == base.id and new_ref.revision == base.revision + 1
    assert case.client.get(f"/api/v1/blocks/{base.id}/body?revision={base.revision}").content == old_body.content
    assert case.client.get(f"/api/v1/blocks/{base.id}/body?revision={new_ref.revision}").content == revised_body.encode()

    notes = case.client.get("/api/v1/notes", params={"ref_id": base.id})
    assert notes.status_code == 200 and len(notes.json()["items"]) == 1
    stale_note = notes.json()["items"][0]
    assert stale_note["revision"] == 2 and stale_note["anchor_state"] == "stale"
    assert stale_note["anchor"] == note.anchor.model_dump(mode="json")
    assert stale_note["markdown"] == note.markdown
    assert case.client.get(f"/api/v1/attempts/{attempt_id}/result").json() == old_grade.json()
    assert grade_history(case.database) == frozen_grade_tables

    stale_index = case.client.get(status_path, params=status_params)
    assert stale_index.status_code == 200 and stale_index.json()["state"] == "stale"
    assert stale_index.json()["index_version"] == ready_index.json()["index_version"]
    assert stale_index.json()["corpus_sha256"] != stale_index.json()["indexed_corpus_sha256"]
    pending_query = case.client.post("/api/v1/retrieval/query", json=query, headers=case.headers)
    assert pending_query.status_code == 200 and pending_query.json()["result_state"] == "not_ready"
    assert pending_query.json()["hits"] == []
