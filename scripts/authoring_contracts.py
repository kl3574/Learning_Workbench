"""Generate independent strict Authoring types; bind only real HTTP operations."""
import json
import re

from scripts.schema_types import generate_types
from services.api.app import authoring_dto as dto

OPERATIONS = {
    ('/api/v1/authoring/jobs', 'post'): ('AuthoringPrepareWrite', 'JobRef', {'202'}),
    ('/api/v1/authoring/jobs', 'get'): (None, 'AuthoringJobPage', {'200'}),
    ('/api/v1/authoring/jobs/{id}', 'get'): (None, 'AuthoringJobView', {'200'}),
    ('/api/v1/authoring/drafts/{id}', 'get'): (None, 'AuthoringDraftView', {'200'}),
    ('/api/v1/authoring/drafts/{id}/numeric-checks', 'post'): ('NumericCheckPreviewWrite', 'NumericCheckView', {'201'}),
    ('/api/v1/authoring/numeric-checks/{id}', 'get'): (None, 'NumericCheckView', {'200'}),
    ('/api/v1/authoring/numeric-checks/{id}/decision', 'post'): ('ApprovalDecision', 'NumericCheckDecisionAck', {'200', '202'}),
}
MODEL_NAMES = (
    'AuthoringBlockRef', 'AuthoringCandidate', 'AuthoringPrepareWrite', 'NumericVariable',
    'NumericAssertion', 'NumericPlan', 'WorkedExampleSymbol', 'WorkedExamplePayload',
    'AuthoringInputMaterial', 'AuthoringPreparationSummary', 'AuthoringValidation',
    'AuthoringJobSummary', 'AuthoringPageQuery', 'AuthoringJobPage', 'AuthoringJobView',
    'AuthoringDraftView', 'NumericCheckPreviewWrite', 'NumericRuntimeProfile',
    'NumericAssertionResult', 'NumericCheckResult', 'NumericCheckView', 'NumericCheckDecisionAck',
    'ApprovalDecision',
)
MAP_NAMES = {
    'AuthoringPrepareWrite', 'AuthoringJobPage', 'AuthoringJobView', 'AuthoringDraftView',
    'NumericCheckPreviewWrite', 'NumericCheckView', 'NumericCheckDecisionAck', 'ApprovalDecision',
}


def authoring_model_artifacts(provenance: dict[str, str]) -> dict[str, str]:
    """Named schema/type evidence alone never claims a registered runtime route."""
    schemas = {name: getattr(dto, name).model_json_schema(mode='serialization') for name in MODEL_NAMES}
    return {'authoring-schemas.json': json.dumps(schemas, ensure_ascii=False, indent=2) + '\n',
            'authoring-types.ts': generate_types(schemas, provenance)}


def authoring_artifacts(ports: str, openapi: dict, provenance: dict[str, str]) -> dict[str, str]:
    marker = 'export interface AuthoringApplicationDTOMap {'
    if ports.count(marker) != 1:
        raise ValueError('Authoring requires one explicit application map')
    block = ports.split(marker, 1)[1].split('}', 1)[0]
    names = re.findall(r'\b(\w+)\s*:\s*unknown\s*;', block)
    if (len(names) != len(set(names)) or set(names) != MAP_NAMES
            or re.sub(r'\b\w+\s*:\s*unknown\s*;', '', block).strip()):
        raise ValueError('Authoring application map must exactly match the declared DTOs')
    components = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request, response, codes) in OPERATIONS.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('Authoring binding requires all seven actual registered operations')
        responses = operation.get('responses', {})
        if {code for code in responses if code.startswith('2')} != codes:
            raise ValueError('Authoring success statuses must preserve approval and decline distinction')
        for code in codes:
            expected = {'application/json': {'schema': {'$ref': '#/components/schemas/'+response}}}
            if responses[code].get('content') != expected:
                raise ValueError('Authoring responses must use the actual named strict model')
        if request is None:
            if 'requestBody' in operation:
                raise ValueError('Authoring reads cannot acquire a body')
        elif operation.get('requestBody') != {'required': True, 'content': {
            'application/json': {'schema': {'$ref': '#/components/schemas/'+request}}}}:
            raise ValueError('Authoring mutation must use its actual required named body')
        if operation.get('security') != [{'LocalSession': []}]:
            raise ValueError('Authoring operations require actual session authentication')
        parameters = operation.get('parameters', [])
        identities = [(p.get('in'), p.get('name', '').lower()) for p in parameters]
        if len(identities) != len(set(identities)):
            raise ValueError('Authoring parameters cannot repeat')
        queries = {p['name']: p for p in parameters if p.get('in') == 'query'}
        headers = {p['name'].lower(): p for p in parameters if p.get('in') == 'header'}
        expected_queries = {'cursor', 'limit'} if response == 'AuthoringJobPage' else set()
        if set(queries) != expected_queries or any(p.get('required') for p in queries.values()):
            raise ValueError('Authoring scalar pagination must match its explicit contract')
        if queries:
            if queries['limit'].get('schema') != {'type':'integer','minimum':1,'maximum':100,'default':20}:
                raise ValueError('Authoring control pagination requires the declared bounded limit')
            if queries['cursor'].get('schema') != {'type':'string','minLength':1}:
                raise ValueError('Authoring cursor is an optional non-null scalar')
        if method == 'post':
            for name in ('origin', 'x-csrf-token', 'idempotency-key'):
                if headers.get(name, {}).get('required') is not True:
                    raise ValueError('Authoring writes require actual Origin/CSRF/original-key guards')
            if headers['idempotency-key'].get('schema') != {'type':'string','pattern':'^[A-Za-z0-9_-]{1,128}$'}:
                raise ValueError('Authoring original key must keep its exact transport contract')
        elif 'idempotency-key' in headers:
            raise ValueError('Authoring reads cannot take a mutation key')
    for name in MAP_NAMES | {'JobRef'}:
        if components.get(name, {}).get('additionalProperties') is not False:
            raise ValueError('Authoring binding requires actual closed named component models')
    artifacts = authoring_model_artifacts(provenance)
    lines = ['// Generated from PRODUCT_DESIGN.md v'+provenance['spec_version']+' and actual runtime OpenAPI.',
             '// spec_sha256: '+provenance['spec_sha256'],
             'import type { AuthoringApplicationDTOMap } from "../module-ports";',
             'import type * as Api from "./api-types";',
             'export interface AuthoringRuntimeDTOMap extends AuthoringApplicationDTOMap {']
    lines.extend('  '+name+': Api.'+name+';' for name in names)
    lines.append('}')
    artifacts['authoring-ports-binding.ts'] = '\n'.join(lines)+'\n'
    return artifacts
