"""Synthetic §20.17 wire examples; no account, process, model or authorization."""
from packages.contracts.canonical import canonical_bytes, sha256_bytes

NOW = '2026-10-04T00:00:00Z'
LATER = '2026-10-04T00:05:00Z'
HASH = 'a' * 64


def samples():
    ref = {'entity': 'block', 'id': 'block_second', 'revision': 1, 'sha256': HASH}
    tools = {'max_tool_calls': 2, 'wall_seconds': 60}
    runtime = {'profile_sha256': HASH, 'cpu_seconds': 60, 'memory_bytes': 2147483648,
               'file_bytes': 16777216, 'protocol_output_bytes': 16777216, 'file_descriptors': 128,
               'processes': 16, 'core_bytes': 0, 'command_network': 'denied', 'writable_area': 'turn_outputs'}
    request = {'message': '  合成说明 😀\n', 'context_refs': [ref], 'expected_session_revision': 2,
               'provider_id': 'provider_one', 'tools': tools}
    material = {'ref': ref, 'title': '合成材料', 'locator': '一', 'character_count': 2, 'excerpt_sha256': HASH}
    warning = {'code': 'SYNTHETIC_WARNING', 'message': '合成说明', 'locator': None, 'severity': 'info'}
    summary = {'context_snapshot_id': 'context_one', 'snapshot_sha256': HASH, 'job_input_sha256': HASH,
               'prepared_input_sha256': HASH, 'runtime': runtime, 'character_count': 20,
               'materials': [material], 'history_turn_ids': [], 'tools': tools, 'warnings': [warning]}
    job = {'id': 'job_one', 'status': 'awaiting_approval'}
    preparation = {'id': 'prepare_one', 'preparation_sha256': HASH, 'actor_session_id': 'actor_one',
                   'session_id': 'session_one', 'session_revision': 3, 'turn_id': 'turn_one', 'job': job,
                   'request': request, 'summary': summary, 'created_at': NOW, 'proposal_id': None,
                   'consent_id': None, 'validity': 'current'}
    budget = {'max_input_tokens': 100, 'max_output_tokens': 50, 'max_provider_calls': 1,
              'max_search_calls': 0, 'max_cost_usd': None}
    outbound = {'version': 'codex-outbound-summary-v1', 'preparation_id': 'prepare_one',
                'preparation_sha256': HASH, 'session_id': 'session_one', 'turn_id': 'turn_one',
                'job_id': 'job_one', 'source_job_revision': 1, 'source_input_sha256': HASH,
                'provider_id': 'provider_one', 'provider_revision': 1, 'config_sha256': HASH,
                'adapter': 'codex_app_server', 'adapter_version': 'synthetic-v1',
                'endpoint': 'https://example.invalid/v1/responses', 'endpoint_policy': 'public_https',
                'model': 'synthetic-model', 'context_snapshot_id': 'context_one',
                'context_snapshot_sha256': HASH, 'input_sha256': HASH, 'request_body_sha256': HASH,
                'messages': [{'role': role, 'character_count': 5, 'content_sha256': HASH}
                             for role in ['system', 'user']],
                'references': [material], 'input_character_count': 20,
                'input_token_assurance': {'kind': 'local_exact', 'input_tokens': 10,
                                         'checker_version': 'synthetic-proof', 'proof_sha256': HASH,
                                         'request_body_sha256': HASH},
                'budget': budget, 'tools': tools, 'runtime': runtime,
                'cost_estimate': {'kind': 'unknown', 'currency': 'USD'},
                'created_at': NOW, 'expires_at': LATER}
    grant = {'id': 'consent_one', 'revision': 1, 'status': 'active', 'actor_session_id': 'actor_one',
             'proposal_id': 'proposal_one', 'proposal_sha256': HASH, 'summary': outbound}
    dispatch = {'id': 'dispatch_one', 'job': {'id': 'job_one', 'status': 'running'},
                'started_at': NOW, 'finished_at': None, 'consumed_provider_calls': 1,
                'input_tokens': None, 'output_tokens': None, 'elapsed_ms': None,
                'cost': {'kind': 'unknown', 'currency': 'USD'}, 'outcome': None, 'error_code': None}
    approval_control = {'id': 'approval_one', 'revision': 1, 'operation_sha256': HASH,
                        'decision': 'pending', 'validity': 'current'}
    consent_control = {'id': 'consent_one', 'revision': 1, 'status': 'active'}
    control = {'id': 'turn_one', 'session_id': 'session_one', 'actor_session_id': 'actor_one',
               'job': job, 'job_revision': 1, 'run_revision': 1, 'last_seq': 0,
               'cancel_requested': False, 'execution': 'not_started', 'outcome': None,
               'approval_ids': ['approval_one'], 'approval_controls': [approval_control],
               'consent_control': consent_control, 'manifest_id': None, 'created_at': NOW,
               'started_at': None, 'finished_at': None, 'error_code': None}
    features = {'approvals': False, 'interrupt': False, 'artifacts': False}
    operation_file = {'path': 'inputs/source.md', 'size': 2, 'sha256': HASH}
    command = {'kind': 'command', 'command_text': 'synthetic-program --check', 'cwd': 'turn_outputs',
               'executable_sha256': HASH, 'environment_sha256': HASH, 'read_files': [operation_file],
               'writable_area': 'turn_outputs', 'filesystem_scope_sha256': HASH,
               'network': 'denied', 'operation_profile_sha256': HASH}
    change = {'path': 'turn_outputs/结果.md', 'action': 'add', 'before_sha256': None,
              'after_sha256': HASH, 'before_size': None, 'after_size': 2, 'diff': '+合成\n'}
    approval = {'id': 'approval_one', 'revision': 1, 'actor_session_id': 'actor_one',
                'session_id': 'session_one', 'turn_id': 'turn_one', 'run_id': 'job_one', 'job': job,
                'job_revision': 1, 'operation': command, 'operation_sha256': HASH,
                'created_at': NOW, 'expires_at': LATER, 'decision': 'pending', 'validity': 'current',
                'execution': 'not_started', 'decided_at': None, 'started_at': None,
                'finished_at': None, 'result_sha256': None, 'error_code': None}
    entry = {'artifact_id': 'artifact_one', 'logical_path': 'results/合成.md', 'size': 2, 'sha256': HASH,
             'media_type': 'text/markdown', 'scan': 'PASS', 'import_kind': 'markdown'}
    excluded = {'entry_id': 'excluded_one', 'reason': 'CODEX_ARTIFACT_REJECTED'}
    manifest = {'version': 'codex-artifact-manifest-v1', 'id': 'manifest_one', 'revision': 1,
                'session_id': 'session_one', 'turn_id': 'turn_one', 'run_id': 'job_one',
                'source_job_id': 'job_one', 'source_outcome': 'failed', 'runtime_profile_sha256': HASH,
                'terminal_receipt_sha256': HASH, 'scan_profile_sha256': HASH, 'created_at': LATER,
                'entries': [entry], 'excluded': [excluded], 'total_bytes': 2,
                'mathematical': 'NOT_RUN', 'sources': 'NOT_RUN', 'independent_pedagogy': 'NOT_RUN'}
    import_item = {'artifact_id': 'artifact_one', 'source_sha256': HASH, 'import_id': 'import_one',
                   'job': {'id': 'import_job', 'status': 'queued'}}
    usage = {'input_tokens': None, 'output_tokens': None}
    answer = '\n 合成 😀  \n'
    result = {
        'CodexBlockRef': ref, 'CodexTurnWarning': warning, 'CodexLocalToolBudget': tools,
        'CodexTurnRuntimeSummary': runtime, 'CodexTurnPrepareWrite': request,
        'CodexTurnPreparationSummary': summary, 'CodexTurnPreparationView': preparation,
        'CodexOutboundBudgetWrite': budget,
        'CodexOutboundPreviewWrite': {'preparation_id': 'prepare_one', 'preparation_sha256': HASH,
            'expected_job_revision': 1, 'expected_provider_revision': 1, 'budget': budget, 'expires_at': LATER},
        'CodexFrozenOutboundSummary': outbound,
        'CodexConsentProposalView': {'id': 'proposal_one', 'proposal_sha256': HASH, 'summary': outbound,
            'validity': 'current', 'consent_id': None, 'warnings': []},
        'CodexConsentCreateWrite': {'proposal_id': 'proposal_one', 'proposal_sha256': HASH},
        'CodexConsentCreateAck': grant,
        'CodexConsentView': {**grant, 'created_at': NOW, 'expires_at': LATER, 'revoked_at': None, 'dispatch': dispatch},
        'CodexDispatchView': dispatch,
        'CodexTurnStartWrite': {'preparation_id': 'prepare_one', 'preparation_sha256': HASH,
            'consent_id': 'consent_one', 'expected_session_revision': 3},
        'CodexTurnStartAck': {'turn_id': 'turn_one', 'session_revision': 4,
                             'job': {'id': 'job_one', 'status': 'queued'}},
        'CodexCurrentFeatures': features,
        'CodexCurrentSessionView': {'id': 'session_one', 'revision': 2, 'status': 'ready',
            'active_turn_id': None, 'adapter_version': 'synthetic-v1', 'capabilities': features},
        'CodexApprovalControl': approval_control, 'CodexConsentControl': consent_control,
        'CodexTurnControlView': control, 'CodexTurnPage': {'items': [control], 'next_cursor': None},
        'CodexTurnResultView': {'control': control, 'preparation_id': 'prepare_one',
            'answer_markdown': answer, 'output_sha256': sha256_bytes(answer.encode()), 'output_state': 'partial',
            'usage': usage, 'mathematical': 'NOT_RUN', 'sources': 'NOT_RUN', 'independent_pedagogy': 'NOT_RUN'},
        'CodexTurnStatusEvent': {'type': 'status', 'job': job, 'run_revision': 1},
        'CodexTurnAnswerEvent': {'type': 'answer_delta', 'text': ' \n'},
        'CodexTurnApprovalEvent': {'type': 'approval_required', 'approval_id': 'approval_one'},
        'CodexTurnUsageEvent': {'type': 'usage', 'usage': usage},
        'CodexTurnManifestEvent': {'type': 'manifest_ready', 'manifest_id': 'manifest_one', 'manifest_sha256': HASH},
        'CodexTurnTerminalEvent': {'type': 'terminal', 'outcome': 'unknown', 'error_code': 'CODEX_OUTCOME_UNKNOWN'},
        'CodexOperationFile': operation_file, 'CodexCommandOperation': command, 'CodexFileChange': change,
        'CodexFileOperation': {'kind': 'file_change', 'files': [change], 'operation_profile_sha256': HASH},
        'CodexDeniedOperation': {'kind': 'unsupported', 'category': 'network', 'reason': 'CODEX_OPERATION_UNSUPPORTED'},
        'GenericApprovalView': approval,
        'GenericApprovalDecisionAck': {'id': 'approval_one', 'revision': 2, 'actor_session_id': 'actor_declining',
            'operation_sha256': HASH, 'decision': 'decline', 'applied': True, 'session_id': 'session_one',
            'turn_id': 'turn_one', 'run_id': 'job_one', 'job': job},
        'CodexInterruptWrite': {'turn_id': 'turn_one', 'expected_session_revision': 3},
        'CodexInterruptAck': {'id': 'session_one', 'turn_id': 'turn_one', 'status': 'interrupt_requested'},
        'CodexArtifactEntry': entry, 'CodexArtifactExcluded': excluded, 'CodexArtifactManifest': manifest,
        'CodexArtifactManifestView': {'manifest': manifest, 'manifest_sha256': sha256_bytes(canonical_bytes(manifest))},
        'CodexArtifactImportWrite': {'turn_id': 'turn_one', 'artifact_ids': ['artifact_one'],
            'expected_manifest_sha256': sha256_bytes(canonical_bytes(manifest))},
        'CodexArtifactImportItem': import_item,
        'CodexArtifactImportView': {'job': {'id': 'aggregate_job', 'status': 'queued'}, 'session_id': 'session_one',
            'turn_id': 'turn_one', 'manifest_sha256': HASH, 'actor_session_id': 'actor_one', 'items': [import_item]},
    }
    result['CodexTurnEvent'] = {'turn_id': 'turn_one', 'run_id': 'job_one', 'seq': 1, 'occurred_at': NOW,
                                'payload': result['CodexTurnStatusEvent']}
    return result
