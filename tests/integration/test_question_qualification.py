"""Real SQLite exact mapping and material-parent checks, without qualification guesses."""

import pytest

from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.question_qualification import question_qualification_facts, review_materials
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from tests.assessment_fixtures import assessment_fixture


@pytest.fixture
def content(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    fixture = assessment_fixture("qualification")
    ContentService(database).publish(workspace, fixture.public_objects, fixture.bodies)
    return database, workspace, fixture


def test_exact_old_concept_and_material_survive_new_current_revision(content):
    database, workspace, fixture = content
    newer = fixture.concept.model_copy(update={"revision": 2, "title": "New exact concept"})
    ContentService(database).publish(workspace, [newer], {})
    with database.connect() as connection:
        facts = question_qualification_facts(connection, workspace, reference(fixture.questions[0]))
        assert facts.mapping_valid and facts.required_concept_ids == [fixture.concept.id]
        assert facts.concept_refs == [reference(fixture.concept)]
        assert facts.max_score == fixture.questions[0].max_score and facts.skill == fixture.questions[0].skill
        materials = review_materials(connection, workspace, facts.question_ref, [reference(fixture.course)])
        assert len(materials) == 1
        assert materials[0].course_ref == reference(fixture.course)
        assert materials[0].lesson_ref == reference(fixture.lesson)
        assert materials[0].block_ref == reference(fixture.block)
        assert materials[0].concept_refs == [reference(fixture.concept)]
        newer_question = fixture.questions[0].model_copy(update={"revision": 2})
    ContentService(database).publish(workspace, [newer_question], {})
    with database.connect() as connection:
        assert question_qualification_facts(connection, workspace, reference(newer_question)).concept_refs == [reference(newer)]
        assert review_materials(connection, workspace, reference(newer_question), [reference(fixture.course)]) == []


def test_missing_mapping_is_unresolved_without_invented_material_or_concept(content):
    database, workspace, fixture = content
    with database.transaction() as connection:
        connection.execute("DELETE FROM object_dependencies WHERE owner_id=? AND relation='concept'", (fixture.questions[0].id,))
    with database.connect() as connection:
        facts = question_qualification_facts(connection, workspace, reference(fixture.questions[0]))
        assert not facts.mapping_valid and facts.concept_refs == []
        assert facts.required_concept_ids == [fixture.concept.id]
        assert review_materials(connection, workspace, facts.question_ref, [reference(fixture.course)]) == []


def test_exact_hash_and_workspace_cannot_be_replaced_for_qualification_or_materials(content):
    database, workspace, fixture = content
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','synthetic','2026-09-14T00:00:00Z')")
    with database.connect() as connection:
        for target_workspace, ref in [("workspace_other", reference(fixture.questions[0])),
            (workspace, reference(fixture.questions[0]).model_copy(update={"sha256": "0" * 64}))]:
            with pytest.raises(ApiError):
                question_qualification_facts(connection, target_workspace, ref)
        with pytest.raises(ApiError):
            review_materials(connection, workspace, reference(fixture.questions[0]),
                [reference(fixture.course).model_copy(update={"sha256": "0" * 64})])


def test_bad_concept_metadata_is_corruption_not_an_unresolved_mapping(content):
    database, workspace, fixture = content
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER revisions_no_update")
        connection.execute("UPDATE revisions SET metadata_json=json_set(metadata_json,'$.title','changed') WHERE object_id=?", (fixture.concept.id,))
    with database.connect() as connection:
        with pytest.raises(ApiError) as failure:
            question_qualification_facts(connection, workspace, reference(fixture.questions[0]))
        assert failure.value.code == "CONTENT_HASH_MISMATCH"
