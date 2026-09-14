from pathlib import Path
import stat
import zipfile

import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json
from packages.contracts.validation import validate_dag, validate_objects, validate_package, validate_route
from scripts.generate_fixtures import generate


@pytest.fixture(scope="module")
def fixtures(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("synthetic"))


def mutate_archive(source: Path, target: Path, transform, extra=()):
    with zipfile.ZipFile(source) as archive:
        files = {entry.filename: archive.read(entry) for entry in archive.infolist()}
    transform(files)
    with zipfile.ZipFile(target, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        for name, data in extra:
            archive.writestr(name, data)
    return target


def refresh_manifest(files):
    manifest = strict_json(files["manifest.json"])
    for entry in manifest["files"]:
        if entry["path"] in files:
            data = files[entry["path"]]
            entry.update(size=len(data), sha256=sha256_bytes(data))
    files["manifest.json"] = canonical_bytes(manifest)


@pytest.mark.parametrize("profile,count", [("author", 12), ("learner", 11)])
def test_generated_profiles_have_valid_raw_and_object_hashes(fixtures, profile, count):
    receipt = validate_package(fixtures / f"course-{profile}.learnpack.zip")
    assert receipt.profile == profile
    assert receipt.payload_count == count
    assert receipt.object_count == 9
    assert receipt.scope == "structure_and_integrity_only"
    if profile == "learner":
        with zipfile.ZipFile(fixtures / f"course-{profile}.learnpack.zip") as archive:
            assert not any(name.startswith("private/") for name in archive.namelist())
            assert b"accepted_answers" not in b"".join(archive.read(name) for name in archive.namelist())


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b", "a\\b", "a//b", "a:b"])
def test_archive_paths_rejected_without_extraction(fixtures, tmp_path, name):
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", lambda files: None, [(name, b"bad")])
    with pytest.raises(ValueError, match="path"):
        validate_package(archive)
    assert not (tmp_path / "escape").exists()


def test_duplicate_zip_paths_rejected(fixtures, tmp_path):
    with pytest.warns(UserWarning, match="Duplicate"):
        archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", lambda files: None,
                                 [("course.json", b"{}")])
    with pytest.raises(ValueError, match="duplicate"):
        validate_package(archive)


def test_unlisted_file_and_private_learner_file_rejected(fixtures, tmp_path):
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", lambda files: None,
                             [("private/secret.json", b"{}")])
    with pytest.raises(ValueError, match="undeclared"):
        validate_package(archive)
    def private_profile(files):
        manifest = strict_json(files["manifest.json"])
        manifest["profile"] = "learner"
        files["manifest.json"] = canonical_bytes(manifest)
    archive = mutate_archive(fixtures / "course-author.learnpack.zip", tmp_path / "private.zip", private_profile)
    with pytest.raises(ValidationError, match="private"):
        validate_package(archive)


def test_raw_hash_corruption_rejected(fixtures, tmp_path):
    def change(files):
        files["content/block_ols.r1.md"] += b"corrupt"
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="raw hash"):
        validate_package(archive)


def test_private_namespace_cannot_claim_learner_visibility(fixtures, tmp_path):
    def change(files):
        manifest = strict_json(files["manifest.json"])
        for entry in manifest["files"]:
            if entry["path"].startswith("private/"):
                entry["visibility"] = "learner"
        files["manifest.json"] = canonical_bytes(manifest)
    archive = mutate_archive(fixtures / "course-author.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="author_private"):
        validate_package(archive)


def test_public_block_cannot_reference_a_private_solution_payload(fixtures, tmp_path):
    def change(files):
        block = strict_json(files["blocks/block_ols.r1.json"])
        block["body_path"] = "private/solutions.jsonl"
        block["body_sha256"] = sha256_bytes(files["private/solutions.jsonl"])
        files["blocks/block_ols.r1.json"] = canonical_bytes(block)
        refresh_manifest(files)
    archive = mutate_archive(fixtures / "course-author.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="public content body"):
        validate_package(archive)


def test_markdown_body_is_not_silently_newline_normalized(fixtures, tmp_path):
    def change(files):
        files["content/block_ols.r1.md"] = files["content/block_ols.r1.md"].replace(b"\n", b"\r\n")
        refresh_manifest(files)
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="body bytes"):
        validate_package(archive)


def test_unrecognized_payload_cannot_be_silently_ignored(fixtures, tmp_path):
    def change(files):
        files["course.json"] = canonical_bytes({"entity": "future_course", "id": "course_ols"})
        refresh_manifest(files)
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="unrecognized"):
        validate_package(archive)


def test_metadata_change_rehashed_file_still_rejects_stale_reference(fixtures, tmp_path):
    def change(files):
        value = strict_json(files["lessons/lesson_ols.r1.json"])
        value["title"] = "changed"
        files["lessons/lesson_ols.r1.json"] = canonical_bytes(value)
        refresh_manifest(files)
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError, match="metadata reference hash"):
        validate_package(archive)


def test_answer_in_public_jsonl_rejected_after_valid_file_hash(fixtures, tmp_path):
    def change(files):
        rows = [strict_json(row) for row in files["questions/public.jsonl"].splitlines()]
        rows[0]["answer"] = "answer-canary"
        files["questions/public.jsonl"] = b"".join(canonical_bytes(row) + b"\n" for row in rows)
        refresh_manifest(files)
    archive = mutate_archive(fixtures / "course-learner.learnpack.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValidationError, match="answer"):
        validate_package(archive)


def test_symlink_and_zip_bomb_rejected(fixtures, tmp_path):
    path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, "../../outside")
    with pytest.raises(ValueError, match="non-regular"):
        validate_package(path)
    path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb", b"0" * 100000)
    with pytest.raises(ValueError, match="ratio"):
        validate_package(path)


@pytest.mark.parametrize("edges", [{"a": ["a"]}, {"a": ["b"], "b": ["a"]}, {"a": ["missing"]}])
def test_dag_rejects_cycles_self_references_and_missing_vertices(edges):
    with pytest.raises(ValueError):
        validate_dag(edges)


def test_dag_supports_deep_acyclic_graph():
    graph = {str(i): [str(i - 1)] if i else [] for i in range(10000)}
    validate_dag(graph)


def test_route_validity_and_duplicate_step_ids(fixtures):
    route = dm.Route.model_validate(strict_json((fixtures / "route.json").read_bytes()))
    validate_route(route)
    duplicate = route.model_copy(update={"steps": route.steps + [route.steps[0]]})
    with pytest.raises(ValueError, match="duplicate"):
        validate_route(duplicate)
    cycle = route.model_dump(mode="json")
    cycle["steps"][0]["requires_steps"] = [cycle["steps"][-1]["id"]]
    with pytest.raises(ValueError, match="cycle"):
        validate_route(dm.Route.model_validate(cycle))


def test_semantics_check_missing_concepts_and_wrong_entity():
    lesson = dm.Lesson(id="lesson_test", revision=1, title="节", objectives=[],
                       block_refs=[dm.ContentRef(entity="concept", id="concept_test", revision=1, sha256="a" * 64)])
    concept = dm.Concept(id="concept_test", revision=1, title="概念")
    lesson.block_refs[0].sha256 = metadata_sha256(concept)
    with pytest.raises(ValueError, match="entity mismatch"):
        validate_objects([lesson, concept], {})
