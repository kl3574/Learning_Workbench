"""Structural package integrity and cross-object semantic checks (M0).

No import transaction, permission decision, mathematical review or product
acceptance is implied by a successful validation receipt.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
import stat
from types import GenericAlias
from typing import cast
import zipfile

from pydantic import BaseModel, Field, create_model

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import metadata_sha256, sha256_bytes, strict_json

MAX_PACKAGE_BYTES = 200 * 1024 * 1024
MAX_PACKAGE_FILES = 2000
MAX_COMPRESSION_RATIO = 100

type PublishedModel = (dm.Course | dm.Lesson | dm.ContentBlock | dm.Concept | dm.Route
                       | dm.QuestionPublic | dm.PracticeSet | dm.AssessmentBlueprint | dm.Note)

ENTITY_MODELS: dict[str, type[PublishedModel]] = {
    "course": dm.Course, "lesson": dm.Lesson, "block": dm.ContentBlock,
    "concept": dm.Concept, "route": dm.Route, "question": dm.QuestionPublic,
    "practice_set": dm.PracticeSet, "assessment": dm.AssessmentBlueprint, "note": dm.Note,
}


@lru_cache(maxsize=16)
def _manifest_model(max_bytes: int, max_files: int) -> type[dm.Manifest]:
    """Keep Appendix B's default schema intact while applying section 10.1 budgets.

    Only resource limits vary; inherited path, visibility, strict-field and
    manifest completeness validators continue to execute without bypasses.
    """
    if (max_bytes, max_files) == (MAX_PACKAGE_BYTES, MAX_PACKAGE_FILES):
        return dm.Manifest
    entry_model = create_model(
        "BudgetFileEntry", __base__=dm.FileEntry,
        size=(int, Field(ge=0, le=max_bytes)),
    )
    return cast(type[dm.Manifest], create_model(
        "BudgetManifest", __base__=dm.Manifest,
        files=(GenericAlias(list, entry_model), Field(min_length=1, max_length=max_files)),
    ))


def parse_manifest(value: object, *, budgets: ImportBudgets = ImportBudgets()) -> dm.Manifest:
    return _manifest_model(budgets.max_package_bytes, budgets.max_package_files).model_validate(value)


def canonical_path(name: str) -> str:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or ".." in path.parts or str(path) != name
            or "\\" in name or ":" in name or "\x00" in name or name == "."):
        raise ValueError("non-canonical package path")
    return name


def validate_dag(edges: Mapping[str, Iterable[str]]) -> None:
    """Check missing vertices and cycles without recursion depth dependence."""
    graph = {node: set(dependencies) for node, dependencies in edges.items()}
    reverse: dict[str, set[str]] = {node: set() for node in graph}
    for node, dependencies in graph.items():
        for dependency in dependencies:
            if dependency not in graph:
                raise ValueError("missing DAG dependency")
            reverse[dependency].add(node)
    pending = [node for node, dependencies in graph.items() if not dependencies]
    visited = 0
    while pending:
        node = pending.pop()
        visited += 1
        for dependent in reverse[node]:
            graph[dependent].remove(node)
            if not graph[dependent]:
                pending.append(dependent)
    if visited != len(graph):
        raise ValueError("dependency cycle")


def refs_in(value: object) -> Iterable[dm.ContentRef]:
    if isinstance(value, dm.ContentRef):
        yield value
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from refs_in(getattr(value, name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from refs_in(item)


def validate_route(route: dm.Route) -> None:
    steps = {step.id: step.requires_steps for step in route.steps}
    if len(steps) != len(route.steps):
        raise ValueError("duplicate route step ID")
    validate_dag(steps)
    required_entity = {"read": {"lesson", "block"}, "practice_submitted": {"practice_set"},
                       "assessment_submitted": {"assessment"}}
    for step in route.steps:
        if step.target.entity not in {"lesson", "block", "practice_set", "assessment"}:
            raise ValueError("unsupported route target entity")
        if step.completion_rule in required_entity and step.target.entity not in required_entity[step.completion_rule]:
            raise ValueError("route completion rule does not match target")


def validate_objects(objects: Iterable[PublishedModel], payloads: Mapping[str, bytes], *,
                     budgets: ImportBudgets = ImportBudgets()) -> dict[tuple[str, str, int], PublishedModel]:
    objects = list(objects)
    registry: dict[tuple[str, str, int], PublishedModel] = {}
    identities: dict[str, str] = {}
    for obj in objects:
        key = (obj.entity, obj.id, obj.revision)
        if key in registry or (obj.id in identities and identities[obj.id] != obj.entity):
            raise ValueError("duplicate content identity")
        registry[key] = obj
        identities[obj.id] = obj.entity
    graph: dict[str, list[str]] = {}
    concept_graph = {obj.id: obj.prerequisite_ids for obj in objects if isinstance(obj, dm.Concept)}
    validate_dag(concept_graph)
    for obj in objects:
        graph_key = f"{obj.entity}:{obj.id}:{obj.revision}"
        graph[graph_key] = []
        for ref in refs_in(obj):
            target = registry.get((ref.entity, ref.id, ref.revision))
            if target is None:
                raise ValueError("reference missing")
            if ref.sha256 != metadata_sha256(target):
                raise ValueError("metadata reference hash mismatch")
            graph[graph_key].append(f"{ref.entity}:{ref.id}:{ref.revision}")
        if isinstance(obj, dm.Course):
            if any(ref.entity != "lesson" for ref in obj.lesson_refs) or any(ref.entity != "concept" for ref in obj.concept_refs):
                raise ValueError("course reference entity mismatch")
        if isinstance(obj, dm.Lesson):
            if any(ref.entity != "block" for ref in obj.block_refs):
                raise ValueError("lesson reference entity mismatch")
            if not set(obj.prerequisite_ids).issubset(concept_graph):
                raise ValueError("lesson prerequisite missing")
        if isinstance(obj, dm.ContentBlock):
            body = payloads.get(canonical_path(obj.body_path))
            if body is None or sha256_bytes(body) != obj.body_sha256:
                raise ValueError("body bytes missing or hash mismatch")
            text = body.decode("utf-8")
            if "\r" in text or len(text) > budgets.max_block_characters:
                raise ValueError("body must use LF and fit text budget")
            if not set(obj.concepts).issubset(concept_graph):
                raise ValueError("block concept missing")
        if isinstance(obj, dm.QuestionPublic) and not set(obj.concept_ids).issubset(concept_graph):
            raise ValueError("question concept missing")
        if isinstance(obj, dm.PracticeSet):
            if obj.lesson_ref.entity != "lesson" or any(ref.entity != "question" for ref in obj.question_refs):
                raise ValueError("practice reference entity mismatch")
        if isinstance(obj, dm.AssessmentBlueprint) and any(ref.entity != "question" for ref in obj.question_refs):
            raise ValueError("assessment reference entity mismatch")
        if isinstance(obj, dm.Route):
            validate_route(obj)
    validate_dag(graph)
    return registry


@dataclass(frozen=True)
class PackageReceipt:
    profile: str
    payload_count: int
    total_bytes: int
    object_count: int
    archive_sha256: str
    scope: str = "structure_and_integrity_only"


def validate_payloads(manifest: dm.Manifest, payloads: Mapping[str, bytes], *,
                      budgets: ImportBudgets = ImportBudgets()) -> int:
    declared = {entry.path for entry in manifest.files}
    if declared != set(payloads):
        raise ValueError("undeclared or missing payload file")
    if len(payloads) + 1 > budgets.max_package_files or sum(map(len, payloads.values())) > budgets.max_package_bytes:
        raise ValueError("package byte budget exceeded")
    for entry in manifest.files:
        data = payloads[entry.path]
        if entry.path.startswith("private/") and entry.visibility != "author_private":
            raise ValueError("private file must declare author_private visibility")
        if len(data) != entry.size or sha256_bytes(data) != entry.sha256:
            raise ValueError("payload size or raw hash mismatch")
    objects: list[PublishedModel] = []
    solutions: list[dm.SolutionPrivate] = []
    symbols: list[dm.Symbol] = []
    citations: list[dm.Citation] = []
    for name, data in payloads.items():
        if not name.endswith((".json", ".jsonl")):
            continue
        if name.endswith(".jsonl"):
            if not data.endswith(b"\n") or b"\r" in data:
                raise ValueError("JSONL must end with LF and contain single-line objects")
            values = [strict_json(line) for line in data.splitlines()]
        else:
            value = strict_json(data)
            values = value if isinstance(value, list) else [value]
        for value in values:
            if not isinstance(value, dict):
                raise ValueError("metadata entry must be an object")
            if name == "private/solutions.jsonl":
                solutions.append(dm.SolutionPrivate.model_validate(value))
            elif name == "symbols.json":
                symbols.append(dm.Symbol.model_validate(value))
            elif name == "sources/citations.json":
                citations.append(dm.Citation.model_validate(value))
            elif value.get("entity") in ENTITY_MODELS:
                if name.startswith("private/") or next(f for f in manifest.files if f.path == name).visibility != "learner":
                    raise ValueError("public metadata placed in private namespace")
                objects.append(ENTITY_MODELS[value["entity"]].model_validate(value))
            elif name != "checks/quality-receipt.json":
                raise ValueError("unrecognized JSON payload")
    root = dm.Course.model_validate(strict_json(payloads[manifest.root_course]))
    visibility = {entry.path: entry.visibility for entry in manifest.files}
    for obj in objects:
        if isinstance(obj, dm.ContentBlock) and (
            obj.body_path.startswith("private/") or visibility.get(obj.body_path) != "learner"
        ):
            raise ValueError("public content body cannot reference private payload")
    registry = validate_objects(objects, payloads, budgets=budgets)
    if ("course", root.id, root.revision) not in registry:
        raise ValueError("root course missing")
    for value in [*solutions, *symbols]:
        if isinstance(value, dm.SolutionPrivate) and value.question_ref.entity != "question":
            raise ValueError("solution must reference a question")
        if isinstance(value, dm.Symbol) and value.first_definition.entity != "block":
            raise ValueError("symbol first definition must reference a block")
        for ref in refs_in(value):
            target = registry.get((ref.entity, ref.id, ref.revision))
            if target is None or metadata_sha256(target) != ref.sha256:
                raise ValueError("solution or symbol reference mismatch")
    citation_ids = {citation.id for citation in citations}
    if len(citation_ids) != len(citations):
        raise ValueError("duplicate citation ID")
    for obj in objects:
        if isinstance(obj, dm.ContentBlock) and not set(obj.citations).issubset(citation_ids):
            raise ValueError("citation missing")
    return len(objects)


def validate_package(archive_path: Path, *, budgets: ImportBudgets = ImportBudgets()) -> PackageReceipt:
    """Read without extracting, checking budgets before decompressing payloads."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > budgets.max_package_files:
            raise ValueError("package file count exceeded")
        names: set[str] = set()
        for entry in entries:
            name = canonical_path(entry.filename)
            if name in names:
                raise ValueError("duplicate ZIP path")
            names.add(name)
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError("ZIP contains non-regular file")
            if entry.file_size > budgets.max_compression_ratio * max(1, entry.compress_size):
                raise ValueError("ZIP compression ratio exceeded")
        if sum(entry.file_size for entry in entries) > budgets.max_package_bytes:
            raise ValueError("package byte budget exceeded")
        if "manifest.json" not in names:
            raise ValueError("manifest missing")
        manifest = parse_manifest(strict_json(archive.read("manifest.json")), budgets=budgets)
        payloads = {name: archive.read(name) for name in names if name != "manifest.json"}
    count = validate_payloads(manifest, payloads, budgets=budgets)
    return PackageReceipt(manifest.profile, len(payloads), sum(map(len, payloads.values())), count,
                          sha256_bytes(archive_path.read_bytes()))
