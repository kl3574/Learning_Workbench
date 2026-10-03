"""Derive Restore numeric model types without inventing HTTP operations."""
import json

from scripts.schema_types import generate_types
from services.api.app import restore_numeric_dto as dto

MODEL_NAMES = (
    'RestoreNumericSourceSpan', 'RestoreNumericVariableBinding', 'RestoreNumericAssertionBinding',
    'RestoreNumericMaterialWrite', 'RestoreNumericMaterialView', 'RestoreNumericCheckPreviewWrite',
    'RestoreNumericCheckView',
)


def restore_numeric_model_artifacts(provenance: dict[str, str]) -> dict[str, str]:
    schemas = {name: getattr(dto, name).model_json_schema(mode='serialization') for name in MODEL_NAMES}
    return {
        'restore-numeric-schemas.json': json.dumps(schemas, ensure_ascii=False, indent=2) + '\n',
        'restore-numeric-types.ts': generate_types(schemas, provenance),
    }
