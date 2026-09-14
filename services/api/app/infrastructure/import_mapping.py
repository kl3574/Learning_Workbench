"""Exact import ID rewriting; references are rehashed from validated dependencies."""

from collections.abc import Mapping
from typing import Any

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from packages.contracts.validation import ENTITY_MODELS, PublishedModel, refs_in, validate_dag

from ..application.errors import ApiError


def invalid() -> ApiError:
    return ApiError(422, "IMPORT_MAPPING_INVALID", "导入 ID 映射或精确引用不完整。")


def object_key(value: PublishedModel | dm.ContentRef) -> str:
    return f"{value.entity}:{value.id}:{value.revision}"


def remap_import(objects: tuple[PublishedModel, ...], solutions: tuple[dm.SolutionPrivate, ...],
                 mapping: Mapping[str, str], *, workspace_id: str, bodies: Mapping[str, bytes],
                 replacements: Mapping[str, PublishedModel] | None = None) -> tuple[
                     tuple[PublishedModel, ...], tuple[dm.SolutionPrivate, ...]]:
    try:
        registry = {object_key(value): value for value in objects}
        if len(registry) != len(objects):
            raise invalid()
        ids = {value.id for value in objects} | {value.id for value in solutions}
        if set(mapping) - ids:
            raise invalid()
        for identifier in mapping.values():
            TypeAdapter(dm.Id).validate_python(identifier, strict=True)
        rewritten_ids = [mapping.get(identifier, identifier) for identifier in ids]
        if len(set(rewritten_ids)) != len(rewritten_ids):
            raise invalid()
        graph = {object_key(value): [object_key(ref) for ref in refs_in(value)] for value in objects}
        validate_dag(graph)
        for value in objects:
            for ref in refs_in(value):
                if metadata_sha256(registry[object_key(ref)]) != ref.sha256:
                    raise invalid()
        result: dict[str, PublishedModel] = {}

        def rewrite(value: Any) -> Any:
            if isinstance(value, dict):
                if set(value) == {"entity", "id", "revision", "sha256"}:
                    ref = dm.ContentRef.model_validate(value)
                    replacement = result[object_key(ref)]
                    return dm.ContentRef(entity=replacement.entity, id=replacement.id, revision=replacement.revision,
                                         sha256=metadata_sha256(replacement)).model_dump(mode="python")
                return {name: rewrite(item) for name, item in value.items()}
            if isinstance(value, list):
                return [rewrite(item) for item in value]
            return value

        pending = list(objects)
        while pending:
            ready = [value for value in pending if all(dependency in result for dependency in graph[object_key(value)])]
            if not ready:
                raise invalid()
            for value in ready:
                if replacements is not None and object_key(value) in replacements:
                    replacement = replacements[object_key(value)]
                    result[object_key(value)] = ENTITY_MODELS[replacement.entity].model_validate(replacement.model_dump(mode="python"))
                    pending.remove(value)
                    continue
                data = rewrite(value.model_dump(mode="python"))
                data["id"] = mapping.get(value.id, value.id)
                for field in ("prerequisite_ids", "concepts", "concept_ids"):
                    if field in data:
                        data[field] = [mapping.get(identifier, identifier) for identifier in data[field]]
                if isinstance(value, dm.Course):
                    for section in data["sections"]:
                        section["lesson_ids"] = [mapping.get(identifier, identifier) for identifier in section["lesson_ids"]]
                if isinstance(value, dm.Note):
                    data["workspace_id"] = workspace_id
                    anchor = value.anchor
                    target = registry.get(object_key(anchor.ref))
                    if data["anchor_state"] == "exact":
                        text = bodies.get(target.body_path, b"").decode("utf-8") if isinstance(target, dm.ContentBlock) else None
                        match = (text is not None and bool(anchor.exact_quote)
                                 and anchor.end_codepoint <= len(text)
                                 and text[anchor.start_codepoint:anchor.end_codepoint] == anchor.exact_quote
                                 and text[:anchor.start_codepoint].endswith(anchor.prefix)
                                 and text[anchor.end_codepoint:].startswith(anchor.suffix))
                        if not match:
                            data["anchor_state"] = "stale" if text is not None else "unresolved"
                result[object_key(value)] = ENTITY_MODELS[value.entity].model_validate(data)
                pending.remove(value)
        private = []
        for solution in solutions:
            target = registry.get(object_key(solution.question_ref))
            if target is None or metadata_sha256(target) != solution.question_ref.sha256:
                raise invalid()
            data = rewrite(solution.model_dump(mode="python"))
            data["id"] = mapping.get(solution.id, solution.id)
            data["review_status"] = "needs_review"
            private.append(dm.SolutionPrivate.model_validate(data))
        return tuple(result[object_key(value)] for value in objects), tuple(private)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise invalid() from None
