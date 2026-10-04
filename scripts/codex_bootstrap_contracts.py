"""Generate strict model seams independently of future runtime registration."""
import json

from scripts.schema_types import generate_types
from services.api.app import codex_bootstrap_dto as dto

MODEL_NAMES = ('CodexBootstrapPreparationWrite', 'CodexBootstrapScope', 'CodexBootstrapPreparationView',
               'CodexBootstrapDecisionAck', 'CodexSessionCreateWrite', 'CodexSessionCreateAck', 'CodexSessionView')


def codex_bootstrap_artifacts(provenance: dict[str, str]) -> dict[str, str]:
    schemas = {name: getattr(dto, name).model_json_schema() for name in MODEL_NAMES}
    return {'codex-bootstrap-types.ts': generate_types(schemas, provenance),
            'codex-bootstrap-schemas.json': json.dumps({'source': provenance, 'schemas': schemas},
                                                       ensure_ascii=False, indent=2) + '\n'}
