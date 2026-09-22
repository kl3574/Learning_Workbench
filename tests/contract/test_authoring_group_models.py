"""Named closed group wire shapes; schema presence does not register HTTP routes."""

import pytest

from services.api.app import authoring_group_dto as g
from services.api.app.application import authoring_group_models as internal


@pytest.mark.parametrize(
    "name",
    [
        "AuthoringLessonPrepareWrite",
        "AuthoringPracticePrepareWrite",
        "AuthoringAssessmentPrepareWrite",
        "AuthoringContentPlan",
        "AuthoringGeneratedBlock",
        "QuestionDraftPublic",
        "GeneratedSolutionAnswer",
        "AuthoringGroupGenerated",
        "AuthoringDraftMemberRef",
        "SolutionDraftPrivate",
        "AuthoringGroupCandidatePayload",
        "AuthoringGroupValidation",
        "AuthoringTargetMaterial",
        "AuthoringGroupJobView",
        "AuthoringGroupDraftView",
        "AuthoringPrivateSolutionView",
        "AuthoringGroupNumericPreviewWrite",
        "AuthoringGroupNumericCheckView",
    ],
)
def test_named_group_models_are_closed_and_all_top_level_fields_required(name):
    schema = getattr(g, name).model_json_schema(mode="serialization")
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(schema["required"])
    assert "default" not in {key for field in schema["properties"].values() for key in field}


@pytest.mark.parametrize(
    "name",
    [
        "AuthoringGroupJobInput",
        "PreparedAuthoringGroupContext",
        "AuthoringContentPlanRecord",
        "AuthoringGroupCandidateRecord",
        "AuthoringGroupNumericJobInput",
    ],
)
def test_internal_records_are_closed_with_no_authority_implicit_defaults(name):
    schema = getattr(internal, name).model_json_schema(mode="serialization")
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(schema["required"])


def test_named_root_unions_are_flat_and_each_real_branch_is_closed():
    for model in (g.AuthoringGroupPrepareWrite, g.AuthoringJobReadView):
        schema = model.model_json_schema(mode="serialization")
        branches = schema.get("oneOf", schema.get("anyOf"))
        assert branches and "properties" not in schema
        for item in branches:
            branch = schema["$defs"][item["$ref"].rsplit("/", 1)[1]]
            assert branch["additionalProperties"] is False
    request = {
        "topic": "合成测试",
        "prerequisites": [],
        "objectives": ["解释"],
        "proof_policy": "full",
        "source_refs": [],
        "provider_id": "provider_one",
        "target_concept_refs": [],
        "output_kind": "lesson",
    }
    value = g.AuthoringGroupPrepareWrite.model_validate(request)
    assert value.model_dump() == request and value.topic == request["topic"]
    assert "root" not in value.model_dump()


@pytest.mark.parametrize(
    "field,value",
    [
        ("consent_id", "fake_consent"),
        ("output_kind", "worked_example"),
        ("objectives", []),
        ("provider_id", None),
        ("target_concept_refs", None),
    ],
)
def test_group_prepare_rejects_missing_or_widened_authority(field, value):
    body = {
        "topic": "合成",
        "prerequisites": [],
        "objectives": ["解释"],
        "proof_policy": "full",
        "source_refs": [],
        "provider_id": "provider_one",
        "target_concept_refs": [],
        "output_kind": "lesson",
    }
    body[field] = value
    with pytest.raises(ValueError):
        g.AuthoringGroupPrepareWrite.model_validate(body)


@pytest.mark.parametrize("field", ["prerequisites", "source_refs", "target_concept_refs"])
def test_required_empty_arrays_cannot_be_silently_defaulted(field):
    body = {
        "topic": "合成",
        "prerequisites": [],
        "objectives": ["解释"],
        "proof_policy": "full",
        "source_refs": [],
        "provider_id": "provider_one",
        "target_concept_refs": [],
        "output_kind": "lesson",
    }
    del body[field]
    with pytest.raises(ValueError):
        g.AuthoringGroupPrepareWrite.model_validate(body)


def test_draft_only_fields_do_not_invent_published_identity_or_private_question_fields():
    question = g.QuestionDraftPublic.model_json_schema()["properties"]
    for field in (
        "answer",
        "accepted_answers",
        "solution",
        "numeric_plan",
        "review_status",
        "id",
        "revision",
        "exposure_group",
    ):
        assert field not in question
    candidate = g.AuthoringGroupCandidate.model_json_schema()["properties"]["entity"]["enum"]
    assert set(candidate) == {"lesson", "practice_set", "assessment"}
    assert g.SolutionDraftPrivate.model_json_schema()["properties"]["review_status"]["const"] == "needs_review"
