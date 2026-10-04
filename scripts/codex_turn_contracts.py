"""Generate named §20.17 contracts without registering future HTTP operations."""
import json

from pydantic import TypeAdapter

from scripts.schema_types import generate_types
from services.api.app import codex_turn_dto as dto


MODEL_NAMES = (
    'CodexBlockRef', 'CodexTurnWarning', 'CodexLocalToolBudget', 'CodexTurnRuntimeSummary',
    'CodexTurnPrepareWrite', 'CodexTurnPreparationSummary', 'CodexTurnPreparationView',
    'CodexOutboundBudgetWrite', 'CodexOutboundPreviewWrite', 'CodexFrozenOutboundSummary',
    'CodexConsentProposalView', 'CodexConsentCreateWrite', 'CodexConsentCreateAck',
    'CodexConsentView', 'CodexDispatchView', 'CodexTurnStartWrite', 'CodexTurnStartAck',
    'CodexCurrentFeatures', 'CodexCurrentSessionView', 'CodexApprovalControl', 'CodexConsentControl',
    'CodexTurnControlView', 'CodexTurnPage', 'CodexTurnResultView',
    'CodexTurnStatusEvent', 'CodexTurnAnswerEvent', 'CodexTurnApprovalEvent', 'CodexTurnUsageEvent',
    'CodexTurnManifestEvent', 'CodexTurnTerminalEvent', 'CodexTurnEvent',
    'CodexOperationFile', 'CodexCommandOperation', 'CodexFileChange', 'CodexFileOperation',
    'CodexDeniedOperation', 'GenericApprovalView', 'GenericApprovalDecisionAck',
    'CodexInterruptWrite', 'CodexInterruptAck', 'CodexArtifactEntry', 'CodexArtifactExcluded',
    'CodexArtifactManifest', 'CodexArtifactManifestView', 'CodexArtifactImportWrite',
    'CodexArtifactImportItem', 'CodexArtifactImportView',
)


def codex_turn_artifacts(provenance: dict[str, str]) -> dict[str, str]:
    schemas = {name: getattr(dto, name).model_json_schema() for name in MODEL_NAMES}
    # Root aliases make the two discriminated unions directly importable, rather
    # than forcing consumers to reconstruct them from an enclosing field.
    schemas['CodexTurnEventPayload'] = {**schemas['CodexTurnEvent']['properties']['payload'],
                                      '$defs': schemas['CodexTurnEvent']['$defs']}
    schemas['CodexOperation'] = {**schemas['GenericApprovalView']['properties']['operation'],
                               '$defs': schemas['GenericApprovalView']['$defs']}
    schemas['SafeCode'] = TypeAdapter(dto.SafeCode).json_schema()
    return {'codex-turn-types.ts': generate_types(schemas, provenance),
            'codex-turn-schemas.json': json.dumps({'source': provenance, 'schemas': schemas},
                                                 ensure_ascii=False, indent=2) + '\n'}
