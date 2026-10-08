"""Internal retained-memory preparation, never a production registration.

Default composition has no resolver or foreign owner. The explicit local-test
composition binds actual SQLite source/config and a named SecretStore capture
before invoking the fixed genuine Rust producer. Synthetic proposal, assurance
and durable-start bytes confer no InputProof for this different genuine body.
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..infrastructure.database import utc_now
from .codex_bootstrap_access import current_control_access
from .errors import ApiError
from .provider_codex_consents import CodexConsentsService, _CodexAuthSnapshot
from .providers import checked_provider_configuration

_SAFE_CODES = frozenset({'CODEX_BINDING_INVALID', 'CODEX_INPUT_PROOF_UNAVAILABLE',
    'CODEX_OUTCOME_UNKNOWN', 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED', 'CODEX_SOURCE_CHANGED',
    'CODEX_CONSENT_REVOKED', 'CODEX_CONSENT_EXPIRED', 'PROVIDER_CONFIGURATION_CHANGED',
    'PROVIDER_SECRET_UNAVAILABLE', 'POLICY_DENIED', 'SESSION_REQUIRED', 'ASSESSMENT_ACTIVE'})


def _failure(code='CODEX_BINDING_INVALID', status=409):
    return ApiError(status, code, '受控请求内存准备已被安全阻止。')


def _safe_failure(error):
    if isinstance(error, ApiError) and error.code in _SAFE_CODES:
        status = 503 if error.code == 'CODEX_INPUT_PROOF_UNAVAILABLE' else 403 if error.code == 'POLICY_DENIED' else 401 if error.code == 'SESSION_REQUIRED' else 409
        return _failure(error.code, status)
    return _failure()


@dataclass(frozen=True, slots=True, repr=False)
class _CoreSourceBinding:
    workspace_id: str
    actor_id: str
    turn_id: str
    dispatch_id: str
    provider_id: str
    provider_revision: int
    config_sha256: str
    source_sha256: str


@dataclass(frozen=True, slots=True, repr=False)
class _ResolvedCoreConstruction:
    """Fixture-only resolver result; typed material is not production authority."""
    binding: _CoreSourceBinding
    facts: dict


@dataclass(slots=True, repr=False)
class _OwnedCoreRequest:
    _owner: object
    _binding: _CoreSourceBinding
    _snapshot: _CodexAuthSnapshot
    # Concrete pinned ctypes owner is loaded by explicit test composition.
    _request: Any
    _released: bool = False

    def _borrow(self, operation):
        if self._released:
            raise _failure()
        try:
            return operation()
        except Exception:
            raise _failure() from None

    def borrow_state(self):
        return self._borrow(self._request.borrow_state)

    def _copy_body_for_owned_verification(self):
        return self._borrow(self._request._copy_body_for_owned_verification)

    def release(self):
        if self._released:
            raise _failure()
        self._released = True
        try:
            self._request.release()
        except Exception:
            raise _failure() from None


class _RetainedCoreRequestOwner:
    """Only internal composition reads source/auth; no HTTP factory or sender."""
    def __init__(self, provider: CodexConsentsService):
        self._provider = provider
        self._resolver = self._foreign = None

    @classmethod
    def _for_local_test(cls, provider, resolver, foreign):
        owner = cls(provider)
        owner._resolver, owner._foreign = resolver, foreign
        return owner

    def _read(self, conn, identity, turn_id):
        current = current_control_access(conn, identity, write=True)
        states, sources = self._provider._states(conn, current)
        state = states.get(turn_id)
        if state is None or state.queued is None or state.granted is None or state.finished is not None:
            raise _failure()
        if state.granted.command.actor_session_id != current.id:
            raise _failure('POLICY_DENIED', 403)
        if state.revoked_at is not None:
            raise _failure('CODEX_CONSENT_REVOKED')
        self._provider.valid_at(state, utc_now())
        self._provider.require_current(conn, current, state, sources[turn_id])
        config = checked_provider_configuration(conn, current, state.proposed.command.ack.summary.provider_id)
        material = sources[turn_id].material
        binding = _CoreSourceBinding(current.workspace_id, current.id, turn_id, state.queued.dispatch_id,
            config.id, config.revision, config.config_sha256,
            sha256_bytes(canonical_bytes(material.model_dump(exclude={'job_revision'}))))
        return current, state, material, config, binding

    @staticmethod
    def _check_source(material):
        context = material.context
        if (material.input.request.context_refs or context.evidence or context.materials
                or context.scopes or context.omitted_refs or context.omitted_scopes):
            raise _failure('CODEX_INPUT_PROOF_UNAVAILABLE', 503)

    @staticmethod
    def _check_construction(facts, material, config, budget):
        # Complete plain-text messages only. Refs requiring a real AppServer
        # resolver are refused, not translated using synthetic request bytes.
        _RetainedCoreRequestOwner._check_source(material)
        context = material.context
        messages = context.messages
        if not messages or messages[0].role != 'system':
            raise _failure()
        expected_input = [{'type': 'message', 'role': item.role,
            'content': [{'type': 'input_text', 'text': item.content}]} for item in messages[1:]]
        provider, prompt = facts['provider'], facts['prompt']
        if (config.adapter != 'official_responses' or provider['base_url'] != config.base_url
                or provider['name'] != config.id or facts['model_info']['slug'] != config.model
                or prompt['base_instructions'] != {'text': messages[0].content, 'provenance': None}
                or prompt['input'] != expected_input
                or facts['metadata']['session_id'] != material.preparation.session_id
                or facts['metadata']['turn_id'] != material.preparation.turn_id
                or type(facts['maximum']) is not int or facts['maximum'] != budget.max_output_tokens
                or type(facts['timeout_ms']) is not int or facts['timeout_ms'] != material.input.runtime.tools.wall_seconds * 1000
                or type(facts['response_body_limit_bytes']) is not int
                or facts['response_body_limit_bytes'] != material.input.runtime.protocol_output_bytes):
            raise _failure()
        if (prompt['tools'] or prompt['parallel_tool_calls'] or prompt['output_schema'] is not None
                or prompt['cyber_access_program'] is not None or facts['auth_mode'] != 'static_api_key_bearer'):
            raise _failure('CODEX_INPUT_PROOF_UNAVAILABLE', 503)
        # Remaining explicit ModelInfo/ResponsesMetadata/affinity facts are
        # checked mechanically by frozen Rust, not authenticated by this owner.

    def prepare(self, identity, turn_id):
        if self._resolver is None or self._foreign is None:
            raise _failure('CODEX_INPUT_PROOF_UNAVAILABLE', 503)
        request = None
        try:
            # Own immediate transaction: configuration writes cannot pass this
            # source/auth/freeze boundary concurrently on a second SQLite writer.
            with self._provider.database.transaction() as conn:
                current, state, material, config, binding = self._read(conn, identity, turn_id)
                if state.started is not None:
                    raise _failure('CODEX_OUTCOME_UNKNOWN')
                self._check_source(material)
                snapshot = self._provider.auth_snapshot(conn, current, state)
                resolved = self._resolver.resolve(conn, current, material, config, binding)
                if type(resolved) is not _ResolvedCoreConstruction or resolved.binding != binding:
                    raise _failure()
                facts = deepcopy(resolved.facts)
                current, state, material, config, actual = self._read(conn, identity, turn_id)
                if actual != binding or state.started is not None:
                    raise _failure()
                self._provider.verify_prepared_auth_snapshot(conn, current, state, snapshot)
                self._check_construction(facts, material, config, state.proposed.command.ack.summary.budget)
                facts['creation_key'] = sha256_bytes(canonical_bytes([binding.workspace_id, binding.turn_id,
                    binding.dispatch_id]))
                try:
                    request = self._foreign.create(facts, b'Bearer ' + snapshot.secret.encode('utf-8'))
                except Exception as error:
                    if type(getattr(error, 'code', None)) is int and error.code == 2:
                        raise _failure('CODEX_NEW_OUTBOUND_CONSENT_REQUIRED') from None
                    raise _failure() from None
                # A raw SecretStore adapter can change outside SQLite locking.
                # Refuse and release if the same capture is no longer current.
                current, state, _, _, actual = self._read(conn, identity, turn_id)
                if actual != binding or state.started is not None:
                    raise _failure()
                self._provider.verify_prepared_auth_snapshot(conn, current, state, snapshot)
            return _OwnedCoreRequest(self, binding, snapshot, request)
        except Exception as error:
            if request is not None:
                try:
                    request.release()
                except Exception:
                    pass
            raise _safe_failure(error) from None

    def verify(self, identity, request):
        """Current-source/auth check, not durable-start or transport permission."""
        try:
            if type(request) is not _OwnedCoreRequest or request._owner is not self or request._released:
                raise _failure()
            with self._provider.database.transaction() as conn:
                current, state, _, _, binding = self._read(conn, identity, request._binding.turn_id)
                if binding != request._binding:
                    raise _failure()
                check = (self._provider.verify_prepared_auth_snapshot if state.started is None
                    else self._provider.verify_auth_snapshot)
                check(conn, current, state, request._snapshot)
        except Exception as error:
            raise _safe_failure(error) from None
