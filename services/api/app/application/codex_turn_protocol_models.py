"""Known offline schema originals, not a runtime profile or InputProof.

The source summary is a reviewed projection of a private historical receipt.
These nine files do not define the complete RPC/session/turn protocol. None of
these closed models grants an owned mapping, approval, dispatch or execution.
"""
from typing import Annotated, Final, Literal, Self

from pydantic import BeforeValidator, ConfigDict, Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes, strict_json
from ..codex_turn_dto import CodexTurnModel
from ..provider_dto import FalseOnly, Zero

ProtocolPath = Literal[
    'v2/TurnStartParams.json', 'v2/ThreadResumeParams.json', 'v2/TurnInterruptParams.json',
    'CommandExecutionRequestApprovalParams.json', 'CommandExecutionRequestApprovalResponse.json',
    'FileChangeRequestApprovalParams.json', 'FileChangeRequestApprovalResponse.json',
    'v2/FileChangePatchUpdatedNotification.json', 'PermissionsRequestApprovalResponse.json',
]
NORMATIVE_SCHEMA_FILES: Final[tuple[tuple[ProtocolPath, int, str], ...]] = (
    ('v2/TurnStartParams.json', 22385, '2dfcf68705896fadc344ccfeb2e9fe5a6bcbbb8b9a90cf449ce232b636daf05a'),
    ('v2/ThreadResumeParams.json', 40510, 'c818e26d830ac4430791eab7d4a872d2384fa6006b14c505d8caf46e7e093527'),
    ('v2/TurnInterruptParams.json', 278, '6dff382dae73d1dbc58406ed045605f647e7a49660e2540fbd2c6c24d60c5f2b'),
    ('CommandExecutionRequestApprovalParams.json', 15559, '16a71816c2d66e319c2c4aa83dd636dfdc43c61e72b6d5475e421ce08d8e6558'),
    ('CommandExecutionRequestApprovalResponse.json', 3202, '6d0767113e22f311381809b6b236b0dde2b99b01992879c26bf7b1ea0e003cb7'),
    ('FileChangeRequestApprovalParams.json', 968, '13848b26814c286ad6425a20d01c1691c86790e1f9e2529399677a8a22fe0d18'),
    ('FileChangeRequestApprovalResponse.json', 1158, 'b95b03ee6be674e25cee2e863cc135a28620e1070addd2f34685aadee27cde08'),
    ('v2/FileChangePatchUpdatedNotification.json', 2159, 'cfb69d18658610a0510f213e09c6847f70517410ed91cf99cc4713c15a795213'),
    ('PermissionsRequestApprovalResponse.json', 7068, '23f3f24e9dbf35db3e0b85703f0d934da5a1cff3cbb611fba8bcd41f3b4a04b0'),
)
SOURCE_PROJECTION_SHA256: Final = 'a31441996822a75015aed858c104e9f82039de88bbeca66d8308bef5fc24af27'


class ProtocolModel(CodexTurnModel):
    model_config = ConfigDict(frozen=True, revalidate_instances='always')


def _integer(value: object) -> object:
    if type(value) is not int:
        raise ValueError('An integer literal is required')
    return value


class ProtocolSchemaIdentity(ProtocolModel):
    path: ProtocolPath
    size: Annotated[int, Field(ge=1, le=65536)]
    sha256: dm.Sha256

    @model_validator(mode='after')
    def fixed_identity(self) -> Self:
        if (self.path, self.size, self.sha256) not in NORMATIVE_SCHEMA_FILES:
            raise ValueError('The exact normative schema identity is required')
        return self


def _members(members: list[ProtocolSchemaIdentity]) -> None:
    if tuple((m.path, m.size, m.sha256) for m in members) != NORMATIVE_SCHEMA_FILES:
        raise ValueError('All nine normative schema members in original order are required')


def verify_internal_refs(schema: dict) -> int:
    """Resolve every embedded ref locally without fetching or expanding refs.

    This is source-closure verification, not a general JSON Schema validator or
    a claim about callback timing or the final hidden model request.
    """
    pending: list[object] = [schema]
    visited = refs = 0
    while pending:
        node = pending.pop()
        visited += 1
        if visited > 20000:
            raise ValueError('The fixed schema source is over the local bound')
        if isinstance(node, dict):
            if '$ref' in node:
                ref = node['$ref']
                if not isinstance(ref, str) or not ref.startswith('#/'):
                    raise ValueError('Only complete internal JSON pointers are supported')
                target: object = schema
                for component in ref[2:].split('/'):
                    # Only canonical JSON-pointer escaping is admitted.
                    index = 0
                    while index < len(component):
                        if component[index] == '~':
                            if index + 1 == len(component) or component[index + 1] not in '01':
                                raise ValueError('Invalid internal JSON pointer')
                            index += 1
                        index += 1
                    key = component.replace('~1', '/').replace('~0', '~')
                    if isinstance(target, dict) and key in target:
                        target = target[key]
                    elif isinstance(target, list) and key.isascii() and key.isdecimal() and str(int(key)) == key:
                        try:
                            target = target[int(key)]
                        except IndexError:
                            raise ValueError('Missing internal schema member') from None
                    else:
                        raise ValueError('Missing internal schema member')
                if not isinstance(target, (dict, bool)):
                    raise ValueError('A ref must resolve to a schema')
                refs += 1
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return refs


class ProtocolSchemaOriginal(ProtocolSchemaIdentity):
    raw_utf8: Annotated[str, Field(min_length=2, max_length=65536, repr=False)]

    @model_validator(mode='after')
    def original_bytes(self) -> Self:
        raw = self.raw_utf8.encode('utf-8')
        if len(raw) != self.size or sha256_bytes(raw) != self.sha256:
            raise ValueError('The original normative schema bytes differ')
        schema = strict_json(raw)
        if not isinstance(schema, dict):
            raise ValueError('An original schema object is required')
        verify_internal_refs(schema)
        return self


class OfflineProtocolSourceSummary(ProtocolModel):
    version: Literal['codex-offline-schema-source-summary-v1']
    scope: Literal['manually_checked_selected9_only']
    original_receipt_sha256: Literal['b64f43cd1b5a7024bcdcb421292cef93b61721ba76a4f325e7663be93931cd9c']
    original_receipt_size: Annotated[Literal[55893], BeforeValidator(_integer)]
    historical_cli_version: Literal['codex-cli0.160.0']
    historical_binary_sha256: Literal['12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad']
    export_profile: Literal['nonexperimental']
    historical_generated_files: Annotated[Literal[314], BeforeValidator(_integer)]
    historical_exit_code: Zero
    historical_generated_at: Literal['2026-10-03T01:09:05.594701+00:00']
    selected_files: Annotated[list[ProtocolSchemaIdentity], Field(min_length=9, max_length=9)]

    @model_validator(mode='after')
    def whole_selected_source(self) -> Self:
        _members(self.selected_files)
        return self


class OfflineProtocolManifest(ProtocolModel):
    version: Literal['codex-offline-turn-protocol-source-v1']
    scope: Literal['selected9_schema_shapes_only']
    implemented: FalseOnly
    source_projection_sha256: Literal['a31441996822a75015aed858c104e9f82039de88bbeca66d8308bef5fc24af27']
    schemas: Annotated[list[ProtocolSchemaIdentity], Field(min_length=9, max_length=9)]

    @model_validator(mode='after')
    def whole_source(self) -> Self:
        _members(self.schemas)
        return self


class OfflineTurnProtocolCatalog(ProtocolModel):
    version: Literal['codex-offline-turn-protocol-catalog-v1']
    scope: Literal['selected9_schema_shapes_only']
    implemented: FalseOnly
    source_projection: OfflineProtocolSourceSummary
    source_projection_sha256: dm.Sha256
    source_projection_utf8: Annotated[str, Field(min_length=2, max_length=8192, repr=False)]
    schemas: Annotated[list[ProtocolSchemaOriginal], Field(min_length=9, max_length=9)]

    @model_validator(mode='after')
    def whole_originals(self) -> Self:
        _members(list(self.schemas))
        raw = self.source_projection_utf8.encode('utf-8')
        if (sha256_bytes(raw) != self.source_projection_sha256 or self.source_projection_sha256 != SOURCE_PROJECTION_SHA256
                or OfflineProtocolSourceSummary.model_validate(strict_json(raw)) != self.source_projection):
            raise ValueError('The checked nonsecret source summary differs')
        return self

    @property
    def source_receipt_sha256(self) -> str:
        return self.source_projection.original_receipt_sha256

    @property
    def internal_ref_occurrences(self) -> int:
        return sum(verify_internal_refs(strict_json(m.raw_utf8)) for m in self.schemas)


class ClosedTurnInterruptParams(ProtocolModel):
    # This is an owned-free shape. Only a future checked owner can bind these
    # external IDs to its actual session/turn; serialization never proves that.
    thread_id: Annotated[str, Field(min_length=1, max_length=240)] = Field(alias='threadId')
    turn_id: Annotated[str, Field(min_length=1, max_length=240)] = Field(alias='turnId')


class ClosedOperationDenial(ProtocolModel):
    decision: Literal['decline', 'cancel']
