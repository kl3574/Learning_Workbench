"""Generate deterministic schemas, TS types and source-linked tracking from the spec."""
# Imports below follow repo-root bootstrapping for standalone CLI execution.
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from packages.contracts.spec_catalog import route_catalog, spec_metadata, traceability
from scripts.extract_spec import PATTERN
from scripts.schema_types import generate_types
from scripts.api_contracts import api_artifacts, runtime_openapi


def recommendation_ports_binding(ports: str, openapi: dict, provenance: dict[str, str]) -> str:
    """Bind the application map only after both real recommendation routes exist."""
    marker = 'export interface RecommendationDTOMap {'
    if ports.count(marker) != 1:
        raise ValueError('recommendation application map must be explicitly declared once')
    block = ports.split(marker, 1)[1].split('}', 1)[0]
    names = re.findall(r'\b(\w+): unknown;', block)
    if (len(names) != len(set(names))
            or set(names) != {'RecommendationPage', 'RecommendationDecisionWrite', 'MutationAck'}
            or re.sub(r'\b\w+: unknown;', '', block).strip()):
        raise ValueError('recommendation application map has unmapped or duplicate DTOs')
    expected = {
        ('/api/v1/recommendations', 'get'): (None, 'RecommendationPage'),
        ('/api/v1/recommendations/{id}/decision', 'post'): ('RecommendationDecisionWrite', 'MutationAck'),
    }
    schemas = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request_name, response_name) in expected.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('recommendation application binding requires both registered runtime operations')
        response = operation.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
        if response != {'$ref': f'#/components/schemas/{response_name}'}:
            raise ValueError('recommendation runtime response does not bind its declared strict DTO')
        if request_name is not None:
            request = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
            if request != {'$ref': f'#/components/schemas/{request_name}'}:
                raise ValueError('recommendation runtime request does not bind its declared strict DTO')
    for name in names:
        schema = schemas.get(name, {})
        if schema.get('type') != 'object' or schema.get('additionalProperties') is not False:
            raise ValueError('recommendation application DTO must be a registered closed object')
    lines = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and runtime OpenAPI; do not edit.",
             f"// spec_sha256: {provenance['spec_sha256']}",
             'import type { RecommendationDTOMap } from "../module-ports";',
             'import type * as Api from "./api-types";', '',
             'export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {']
    lines.extend(f'  {name}: Api.{name};' for name in names)
    lines.append('}')
    return '\n'.join(lines) + '\n'


def artifacts(root: Path = ROOT) -> dict[Path, bytes]:
    spec = root / "PRODUCT_DESIGN.md"
    provenance = spec_metadata(spec)
    schemas = {name: model.model_json_schema() for name, model in sorted(dm.CONTRACTS.items())}
    output: dict[Path, bytes] = {}

    def add_json(path: str, data: object) -> None:
        output[root / path] = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    for name, schema in schemas.items():
        add_json(f"packages/contracts/generated/schemas/{name}.schema.json", {
            "$schema": "https://json-schema.org/draft/2020-12/schema", "$comment": "Generated; do not edit.",
            "x-source-spec": provenance, **schema,
        })
    add_json("packages/contracts/generated/manifest.json", {**provenance, "models": sorted(schemas)})
    embedded = [{"path": path, "source_block_sha256": sha256_bytes((body + "\n").encode("utf-8"))}
                for path, body in PATTERN.findall(spec.read_text(encoding="utf-8"))]
    add_json("packages/contracts/generated/spec-sources.json", {**provenance, "embedded_files": embedded,
             "note": "Embedded source hashes preserve provenance; evolved implementation files need not remain byte-identical."})
    output[root / "packages/contracts/generated/types.ts"] = generate_types(schemas, provenance).encode()
    ports = (root / "packages/contracts/module-ports.ts").read_text(encoding="utf-8")
    dto_block = ports.split("export interface DTOMap {", 1)[1].split("}", 1)[0]
    names = re.findall(r"\b(\w+): unknown;", dto_block)
    if not names or set(names) - set(schemas):
        raise ValueError("module ports require unmapped shared models")
    binding = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']}; do not edit.",
               f"// spec_sha256: {provenance['spec_sha256']}",
               'import type { DTOMap } from "../module-ports";',
               'import type * as Model from "./types";', "", "export interface DomainDTOMap extends DTOMap {"]
    binding.extend(f"  {name}: Model.{name};" for name in names)
    binding.append("}")
    output[root / "packages/contracts/generated/module-ports-binding.ts"] = ("\n".join(binding) + "\n").encode()
    tracking = traceability(spec)
    add_json("docs/requirements/traceability.json", tracking)
    catalog = route_catalog(spec)
    add_json("docs/requirements/routes.json", catalog)
    openapi = runtime_openapi()
    application_binding = recommendation_ports_binding(ports, openapi, provenance)
    output[root / 'packages/contracts/generated/recommendation-ports-binding.ts'] = application_binding.encode()
    for name, value in api_artifacts(openapi, catalog, provenance).items():
        target = "packages/contracts/generated/" + name
        if isinstance(value, str):
            output[root / target] = value.encode("utf-8")
        else:
            add_json(target, value)
    lines = ["# 派生需求追踪（不是产品验收结果）", "", f"来源：PRODUCT_DESIGN.md v{provenance['spec_version']}",
             f"spec_sha256: `{provenance['spec_sha256']}`", "", "由 `scripts/generate_contracts.py` 生成；实现和测试事实见 progress/state.json。",
             "", "| 需求 | 优先级 | 任务 | 目标场景 |", "|---|---|---|---|"]
    for req in tracking["requirements"]:
        lines.append(f"| {req['id']} {req['title']} | {req['priority']} | {', '.join(req['task_ids'])} | {', '.join(req['scenario_ids'])} |")
    output[root / "docs/requirements/README.md"] = ("\n".join(lines) + "\n").encode()
    return output


def generate(root: Path = ROOT, check: bool = False) -> int:
    result = artifacts(root)
    mismatches = []
    for path, data in result.items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                mismatches.append(str(path.relative_to(root)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    expected_schemas = {path for path in result if path.suffix == ".json" and path.parent.name == "schemas"}
    existing_schemas = set((root / "packages/contracts/generated/schemas").glob("*.json"))
    if existing_schemas - expected_schemas:
        mismatches.extend(str(path.relative_to(root)) for path in existing_schemas - expected_schemas)
    if mismatches:
        raise ValueError("generated artifacts are stale: " + ", ".join(sorted(mismatches)))
    return len(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"{'Checked' if args.check else 'Generated'} {generate(check=args.check)} artifacts")
