"""Small fail-closed JSON Schema to TypeScript projection for our shared models.

The supported subset is exercised against every generated Pydantic schema;
new schema constructs fail generation rather than silently becoming any.
"""
from __future__ import annotations

import json
from typing import Any


def typescript_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[1]
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    if "enum" in schema:
        return " | ".join(json.dumps(value, ensure_ascii=False) for value in schema["enum"])
    for keyword, operator in (("anyOf", " | "), ("oneOf", " | "), ("allOf", " & ")):
        if keyword in schema:
            return "(" + operator.join(typescript_type(item) for item in schema[keyword]) + ")"
    kind = schema.get("type")
    if kind in ("string", "boolean", "null"):
        return kind
    if kind in ("integer", "number"):
        return "number"
    if kind == "array":
        return f"Array<{typescript_type(schema['items'])}>"
    if kind == "object":
        if schema.get("additionalProperties") is not False:
            raise ValueError("unbounded object schema not supported")
        required = set(schema.get("required", []))
        if not schema.get("properties"):
            return "Record<string, never>"
        fields = []
        for name, value in schema.get("properties", {}).items():
            optional = "" if name in required else "?"
            fields.append(f"  {json.dumps(name)}{optional}: {typescript_type(value)};")
        return "{\n" + "\n".join(fields) + "\n}"
    raise ValueError(f"unsupported JSON Schema construct: {schema}")


def generate_types(schemas: dict[str, dict], provenance: dict[str, str]) -> str:
    definitions = dict(schemas)
    for schema in schemas.values():
        for name, definition in schema.get("$defs", {}).items():
            if name not in definitions:
                definitions[name] = definition
    header = (f"// Generated from {provenance['source']} v{provenance['spec_version']}. DO NOT EDIT.\n"
              f"// spec_sha256: {provenance['spec_sha256']}\n"
              "// JSON Schema is the type source; runtime semantic checks remain required.\n\n")
    return header + "\n\n".join(f"export type {name} = {typescript_type(schema)};"
                                for name, schema in sorted(definitions.items())) + "\n"
