"""Independent file-only review of exactly admitted immutable CI text candidates.
No API, observer execution, product tests, Git writes, private raw log/ZIP access.
"""
from pathlib import Path, PurePosixPath
import datetime, hashlib, json, re, stat

base = Path('$HOME/.cache/learning-workbench-acceptance/m63-ci-public6671-observation-oct05')
out = Path(__file__).parent
source = '6671dd5c924edbac8ca7f479c4f51d4afec14480'
pr_checkout = 'ab37ef8a4e91ddacd284f83b052b659e70425359'
fixed = {37234694749: 'push', 37234699481: 'pull_request'}
sha = lambda b: hashlib.sha256(b).hexdigest()
read_bindings, findings, checks = [], [], []

def check(condition, name, detail=None):
    checks.append({'check': name, 'pass': bool(condition)})
    if not condition:
        findings.append({'check': name, 'detail': detail})

def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result

def read(path, label):
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError('non-regular admitted input: ' + label)
    data = path.read_bytes()
    read_bindings.append({'file': label, 'size_bytes': len(data), 'sha256': sha(data)})
    data.decode('utf-8', errors='strict')
    return data

outer_bytes = read(base / 'FINAL_OUTER_ALLOWLIST-57.json', 'FINAL_OUTER_ALLOWLIST-57.json')
outer = json.loads(outer_bytes, object_pairs_hook=no_duplicates)
check(outer['candidate_base'] == 'safe-share-57', 'outer-fixed-candidate-base')
check([x['file'] for x in outer['allowed_outer_files']] == ['SAFE_CANDIDATES-57.json', 'PACKET_READBACK-57.json'], 'outer-exact-two-metadata')
outer_data = {}
for entry in outer['allowed_outer_files']:
    data = read(base / entry['file'], entry['file'])
    check(sha(data) == entry['sha256'], 'outer-sha-' + entry['file'])
    outer_data[entry['file']] = json.loads(data, object_pairs_hook=no_duplicates)
manifest = outer_data['SAFE_CANDIDATES-57.json']
owner_readback = outer_data['PACKET_READBACK-57.json']
check(manifest['candidate_base'] == 'safe-share-57' and manifest['source_commit'] == source, 'manifest-base-source')
check(len(manifest['entries']) == 88, 'manifest-exact88')
check(owner_readback['candidate_count'] == 88, 'owner-readback-exact88')
check(owner_readback['candidate_manifest_sha256'] == sha((base / 'SAFE_CANDIDATES-57.json').read_bytes()), 'owner-manifest-sha')
check(owner_readback['raw_original_recheck_count'] == 113 == manifest['original_immutable_recheck_count'], 'owner-original-recheck-count-metadata-only113')

entries, data_by_name, objects = {}, {}, {}
for entry in manifest['entries']:
    name = entry['file']
    parsed = PurePosixPath(name)
    check(not parsed.is_absolute() and '..' not in parsed.parts and '\\' not in name, 'safe-relative-' + name)
    check(name not in entries, 'unique-member-' + name)
    entries[name] = entry
    data = read(base / 'safe-share-57' / name, 'safe-share-57/' + name)
    data_by_name[name] = data
    check(len(data) == entry['size_bytes'] and sha(data) == entry['sha256'], 'candidate-size-sha-' + name)
    check(entry['inspect_findings'] == [], 'owner-inspect-empty-' + name)
    if name.endswith('.json'):
        objects[name] = json.loads(data, object_pairs_hook=no_duplicates)
    if 'source_relative' in entry:
        check(owner_readback['raw_original_hashes'][entry['source_relative']] == entry['original_sha256'], 'original-metadata-binding-' + name)
        if entry['transformation'] == 'identity':
            check(entry['sha256'] == entry['original_sha256'], 'identity-candidate-original-sha-' + name)
check({x['file']: (x['size_bytes'], x['sha256']) for x in owner_readback['readback']} == {n: (e['size_bytes'], e['sha256']) for n,e in entries.items()}, 'owner-readback-exact-member-bindings')

snapshot = objects['api-captures/57-SNAPSHOT.json']
api = objects['FINAL_API_READBACK.json']
check(snapshot['source'] == source and snapshot['sequence'] == 57, 'snapshot57-fixed-source')
check(snapshot['observed_utc'] == '2026-10-04T22:20:03.336053+00:00', 'snapshot57-original-time')
check(len(snapshot['actual_events']) == 2 and {e['id']:e['event'] for e in snapshot['actual_events']} == fixed, 'exact-two-original-events')
check(api['source'] == source and api['snapshot_sha256'] == sha(data_by_name['api-captures/57-SNAPSHOT.json']), 'derived-api-snapshot-binding')
check(api['run_api_sha256'] == owner_readback['raw_original_hashes'][api['run_api_original_file']], 'original-run-api-sha-metadata-only')
snapshot_jobs = {}
for event in snapshot['actual_events']:
    rid = event['id']
    check(event['status'] == 'completed' and event['conclusion'] == 'success' and event['run_attempt'] == 1 and event['head_sha'] == source, 'terminal-original-attempt1-' + str(rid))
    check(len(event['jobs']) == 6 and {j['name'] for j in event['jobs']} == {'backend','frontend','browser','integration','spec-contracts','security-publication'}, 'six-distinct-gates-' + str(rid))
    for job in event['jobs']:
        check(job['status'] == 'completed' and job['conclusion'] == 'success', 'terminal-job-' + str(job['id']))
        snapshot_jobs[job['id']] = (rid, job)
    a = next(x for x in api['runs'] if x['id'] == rid)
    check(all(a[k] == event[k] for k in ['id','event','status','conclusion','run_attempt','head_sha','created_at','updated_at','html_url']), 'api-derived-run-fields-' + str(rid))

jobs = objects['FINAL_JOB_LOG_READBACK.json']['jobs']
excerpts = {x['job_id']:x for x in objects['BOUNDED_ORIGINAL_LOG_EXCERPTS.json']['logs']}
check(len(jobs) == 12 and {j['job_id'] for j in jobs} == set(snapshot_jobs) == set(excerpts), 'exact12job-logs-and-excerpts')
job_bindings, event_counts = [], {}
for job in jobs:
    jid, rid, name = job['job_id'], job['run_id'], job['name']
    srid, sj = snapshot_jobs[jid]
    check(srid == rid and fixed[rid] == job['event'] and all(job[k] == sj[k] for k in ['name','status','conclusion','started_at','completed_at']), 'snapshot-job-metadata-' + str(jid))
    raw = job['raw_log']
    check(owner_readback['raw_original_hashes'][raw['file']] == raw['sha256'], 'raw-log-sha-metadata-' + str(jid))
    receipt = objects['job-captures/' + raw['capture_receipt']]
    command = objects['job-captures/job-' + str(jid) + '-logs-01-command.json']
    check(receipt['exit_code'] == 0 and receipt['status'] == 'ACTUAL_COMPLETE_JOB_LOG_CAPTURED' and receipt['stdout_sha256'] == raw['sha256'] and receipt['stdout_bytes'] == raw['size_bytes'] and receipt['stderr_bytes'] == 0, 'capture-receipt-' + str(jid))
    check(receipt['job_id'] == jid and receipt['run_id'] == rid and receipt['job_name'] == name and receipt['event'] == fixed[rid], 'receipt-job-identity-' + str(jid))
    check(any('jobs/' + str(jid) + '/logs' in str(v) for v in command['argv']), 'specific-log-command-endpoint-' + str(jid))
    ex = excerpts[jid]
    check(ex['raw_log_file'] == raw['file'] and ex['raw_log_sha256'] == raw['sha256'], 'excerpt-raw-metadata-' + str(jid))
    rows = {r['line']:r for r in ex['rows']}
    for row in ex['rows']:
        check(sha(row['original_line'].encode()) == row['original_line_sha256'], 'original-selected-line-checksum-' + str(jid) + '-' + str(row['line']))
        check(1 <= row['line'] <= raw['line_count'], 'excerpt-original-line-range-' + str(jid) + '-' + str(row['line']))
    expected_checkout = source if fixed[rid] == 'push' else pr_checkout
    checkout = job['actual_checkout']
    check(checkout['sha'] == expected_checkout and expected_checkout in rows[checkout['sha_line']]['original_line'], 'actual-checkout-excerpt-' + str(jid))
    check(rows[raw['line_count']]['original_line'].endswith('Cleaning up orphan processes'), 'complete-log-terminal-excerpt-' + str(jid))
    counts = event_counts.setdefault(str(rid), {'event': fixed[rid]})
    gates = job['actual_gates']
    if name == 'backend':
        check(gates['pytest']['collected'] == gates['pytest']['passed'] == 926 and gates['pytest']['warnings'] == 2 and gates['mypy']['source_files'] == 287, 'actual-backend-counts-' + str(rid))
        counts['backend_passed'] = 926
        counts['mypy_files'] = 287
    if name == 'frontend':
        check(gates['vitest']['tests_passed'] == gates['vitest']['tests_total'] == 1421 and gates['vitest']['test_files_passed'] == gates['vitest']['test_files_total'] == 167, 'actual-Web-counts-' + str(rid))
        counts['Web_passed'] = 1421
        counts['Web_test_files'] = 167
    if name == 'security-publication':
        check(gates['publication_path_and_credential_scan']['scanned_staged_tracked_files'] == 21841 and gates['publication_path_and_credential_scan']['manual_provenance_review_remains_required'] is True, 'bounded-publication-scan-' + str(rid))
        counts['bounded_publication_scanned'] = 21841
    if name == 'spec-contracts':
        check(gates['pytest']['collected'] == gates['pytest']['passed'] == 962 and gates['pytest']['warnings'] == 2, 'actual-spec-counts-' + str(rid))
        spec = gates['make_verify_spec']['original_json_metadata']
        check(spec['scope'] == 'M0_structural_baseline_only' and spec['spec_sha256'] == 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec' and all(spec[k] == 'NOT_RUN' for k in ['real_codex','real_provider','learning_effectiveness','product_acceptance']) and spec['publication'] == 'NOT_CHECKED', 'M0-only-qualification-' + str(rid))
        counts['spec_passed'] = 962
    if name == 'integration':
        gate = gates['pytest']
        check(gate['actual_counts'] == {'collected':2469,'passed':2467,'skipped':2,'warnings':2}, 'actual-integration-counts-' + str(rid))
        summary = gate['original_terminal_summary']
        check(summary['original_summary'] in rows[summary['line']]['original_line'], 'integration-original-summary-' + str(rid))
        check(len(gate['original_individual_skips']) == 2 and {s['original_test_path'] for s in gate['original_individual_skips']} == {'tests/integration/test_authoring_numeric_runtime.py','tests/integration/test_restore_numeric_actual_runtime.py'}, 'two-actual-numeric-ENV-skips-' + str(rid))
        for skip in gate['original_individual_skips']:
            check('BLOCKED_ENVIRONMENT' in skip['original_reason'] and skip['original_summary'] in rows[skip['original_log_line']]['original_line'], 'original-ENV-skip-excerpt-' + str(rid) + '-' + str(skip['original_log_line']))
        counts['integration'] = gate['actual_counts']
        counts['integration_seconds'] = gate['original_elapsed_seconds']
    if name == 'browser':
        gate = gates['browser']
        result_rows = [r for r in objects['BROWSER_PASSED_TEST_ROWS.json']['rows'] if r['run_id'] == rid]
        check(len(result_rows) == 133 and {r['ordinal'] for r in result_rows} == set(range(1,134)) and len({r['identity'] for r in result_rows}) == 133, 'independent133-browser-identities-ordinals-' + str(rid))
        for row in result_rows:
            check(row['job_id'] == jid and sha(row['original_line'].encode()) == row['original_line_sha256'], 'browser-original-row-binding-' + str(rid) + '-' + str(row['ordinal']))
            check(re.search(r'✓\s+' + str(row['ordinal']) + r'\s+' + re.escape(row['identity']) + r' \(' + re.escape(row['duration']) + r'\)', row['original_line']) is not None, 'browser-original-PASS-row-parse-' + str(rid) + '-' + str(row['ordinal']))
        check(gate['summary_passed_count'] == gate['declared_test_count'] == gate['parsed_passed_result_row_count'] == 133 and gate['declared_worker_count'] == 1 and gate['failure_or_skipped_result_row_lines'] == [], 'browser-gate-summary-' + str(rid))
        check(gate['summary']['original_summary'] in rows[gate['summary']['line']]['original_line'], 'browser-original-terminal-summary-' + str(rid))
        helper = objects['readbacks/' + ('PUSH' if fixed[rid] == 'push' else 'PR') + '_BROWSER_LOG_READBACK.json']
        step = {s['number']:s for s in helper['allowed_original_jobs_snapshot']['relevant_original_steps']}
        check(step[12]['conclusion'] == step[13]['conclusion'] == 'success' and step[14]['conclusion'] == 'skipped', 'actual-numeric-upload-and-failure-upload-skipped-' + str(rid))
        counts['browser_passed'] = 133
        counts['browser_duration_original'] = gate['original_reported_duration']
        counts['failure_only_diagnostic_upload'] = 'SKIPPED_NOT_RUN'
    job_bindings.append({'run_id':rid,'event':fixed[rid],'job_id':jid,'name':name,'raw_log_sha256_metadata':raw['sha256'],'raw_log_bytes_metadata':raw['size_bytes'],'raw_log_lines_metadata':raw['line_count'],'actual_checkout':expected_checkout,'full_raw_log_reread_by_this_reviewer':False,'selected_excerpt_rows':len(ex['rows'])})

checkout = objects['CHECKOUT_TREE_READBACK.json']
commits = {x['sha']:x for x in checkout['commits']}
check(commits[source]['tree'] == commits[pr_checkout]['tree'] == 'fe6a9cf44dd29071d45af2172fac225ae100272b', 'source-PR-merge-equal-tree-metadata')
check(commits[pr_checkout]['parents'] == ['e2877101d9c2bda0f793a460db63ef496350c6b4',source], 'PR-merge-original-parent-metadata')
check(objects['FINAL_JOB_LOG_READBACK.json']['CI_working_input_before_after_maps'] == 'NOT_CAPTURED_BY_THIS_READONLY_OBSERVER', 'no-CI-runtime-before-after-maps-inferred')
watcher = objects['WATCHER_TERMINAL_TOOL_READBACK.json']
check(watcher['actual_tool_exit_code'] == 0 and watcher['final_cycle'] == 53 and watcher['final_snapshot'] == '57-SNAPSHOT.json', 'parent-terminal-tool-qualification-metadata')
for label in ['observe','logs']:
    stem = 'watcher/watch-cycle-053-' + label
    receipt = objects[stem + '-receipt.json']
    check(receipt['exit_code'] == 0 and receipt['stdout_sha256'] == sha(data_by_name[stem + '.stdout']), 'final-child-exit0-stdout-' + label)
check(json.loads(data_by_name['watcher/watch-cycle-053-observe.stdout'])['sequence'] == 57, 'watcher-final-observe-sequence57')
check('time.sleep(75)' in data_by_name['watcher/watch-fixed-events.py'].decode(), 'watcher-source-single75sec-loop-readonly-not-executed')

artifacts = objects['ACTUAL_ARTIFACT_READBACK.json']['artifacts']
check(len(artifacts) == 4 and len({x['artifact_id'] for x in artifacts}) == 4, 'exact4ZIP-metadata-not-byte-open')
numeric_rows, actual_by_run, numeric_id_hashes = [], {}, {}
for artifact in artifacts:
    aid, rid = artifact['artifact_id'], artifact['run_id']
    md = objects['artifact-metadata/artifact-' + str(aid) + '-zip-01-READBACK.json']
    receipt = objects['artifact-metadata/artifact-' + str(aid) + '-zip-01-receipt.json']
    check(md['receipt'] == artifact['receipt'] == receipt, 'artifact-receipt-metadata-exact-' + str(aid))
    check(receipt['exit_code'] == 0 and receipt['api_digest'] == 'sha256:' + receipt['stdout_sha256'] and receipt['stdout_bytes'] == receipt['api_size_in_bytes'] and receipt['actual_digest_matches_api'] is True and receipt['actual_size_matches_api'] is True, 'artifact-API-digest-size-consistency-metadata-only-' + str(aid))
    check(artifact['ZIP_publication'] == 'NOT_ADMITTED' and md['zip_publication'] == 'NOT_ADMITTED', 'private-ZIP-not-admitted-' + str(aid))
    check(receipt['stdout_sha256'] == owner_readback['raw_original_hashes']['artifact-' + str(aid) + '-zip-01.zip'], 'owner-private-ZIP-digest-binding-metadata-only-' + str(aid))
    for member in artifact['members']:
        name = 'numeric-json/' + member['selected_file']
        entry = entries[name]
        check(entry['size_bytes'] == member['file_size'] and entry['sha256'] == member['sha256'], 'selected-DTO-member-bytes-' + name)
        dto = objects[name]
        actual, result = dto['actual'], dto['actual']['result']
        publish = dto['outcome'] if 'outcome' in dto else dto['publishOutcome']
        check(actual['job']['status'] == 'failed' and result['job_id'] == actual['job']['id'] and result['outcome'] == 'environment_unavailable' and result['verdict'] == 'BLOCKED' and result['exit_code'] == 1 and result['assertions'] == [], 'actual-numeric-blocked-no-assertions-' + name)
        check(publish['status'] == 409 and publish['body']['error']['code'] == 'PUBLISH_NUMERIC_REQUIRED' and publish['body']['error']['retryable'] is False, 'actual-publication409-' + name)
        id_hash = sha(actual['job']['id'].encode())
        actual_by_run.setdefault(rid,[]).append(actual)
        numeric_id_hashes[member['selected_file']] = id_hash
        presence = {key:{'present':key in dto, 'value':dto[key] if key in dto else 'ABSENT_NOT_DEFAULTED'} for key in ['externalModelCalls','loopbackCalls','newModelCalls','physicalNumeric','published']}
        if 'finalDraft' in dto:
            check('published' in dto and dto['published'] is None and dto['finalDraft']['state'] == 'draft' and 'published_ref' in dto['finalDraft'] and dto['finalDraft']['published_ref'] is None, 'single-draft-explicit-unpublished-' + name)
            check(dto['externalModelCalls'] == 0 and dto['loopbackCalls'] == 1 and dto['physicalNumeric'] == 'BLOCKED', 'explicit-single-loopback-no-externalmodel-' + name)
        numeric_rows.append({'run_id':rid,'artifact_id':aid,'file':name,'actual_job_id_sha256':id_hash,'numeric':'FAILED_ENVIRONMENT_UNAVAILABLE_BLOCKED_EXIT1_NO_ASSERTIONS','publish':'HTTP409_PUBLISH_NUMERIC_REQUIRED','field_presence':presence})
check(len(numeric_rows) == 6 and len(set(numeric_id_hashes.values())) == 4, '6DTO4distinct-logical-jobs-not-executions')
for rid, actuals in actual_by_run.items():
    check(len(actuals) == 3 and len({x['job']['id'] for x in actuals}) == 2, 'each-event3DTO2logical-jobs-' + str(rid))
    duplicates = [a for a in actuals if a['job']['id'].startswith('restore_numeric_job_')]
    check(len(duplicates) == 2 and duplicates[0] == duplicates[1], 'Restore-duplicate-full-actual-equality-' + str(rid))
dedup = objects['readbacks/NUMERIC_DTO_DEDUPLICATION.json']
check(dedup['distinct_actual_job_descriptors_across_two_runs'] == 4 and {x['file']:x['actual_job_id_sha256'] for x in dedup['rows']} == numeric_id_hashes, 'owner-dedup-matches-independent-originalDTO-hashes')
owner_report = objects['REPORT.json']
check(all(word in owner_report['prior_evidence_preserved'] for word in ['terminalFAIL','UNKNOWN','LOSS']), 'oldFAIL-UNKNOWN-LOSS-not-upgraded')
check(owner_report['observer_actions']['external_model_calls'] == 0 and owner_report['observer_actions']['remote_write'] == 0, 'owner-actions-exact-metadata-no-new-reviewer-actions')
workflow = objects['source/PINNED_WORKFLOW_SOURCE.json']
check(workflow['source_commit'] == source and workflow['stdout_sha256'] == sha(data_by_name['source/PINNED_WORKFLOW_SOURCE.stdout']), 'pinned-workflow-source-candidate-byte-binding')

result = {
    'schema':'IndependentCI6671TerminalCandidateReadback/v1',
    'status':'PASS_WITH_EXPLICIT_EVIDENCE_LIMITS' if not findings else 'FINDINGS_REVIEW_REQUIRED',
    'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_commit':source,
    'reviewer_scope':'Exactly FINAL_OUTER_ALLOWLIST-57.json, its2outer metadata and88 explicit UTF8 text candidates; no other private input read.',
    'input_bindings':read_bindings,
    'candidate_count':len(entries),
    'candidate_bytes':sum(len(b) for b in data_by_name.values()),
    'check_count':len(checks),'checks':checks,'findings':findings,
    'terminal_snapshot':{'sequence':57,'observed_utc':snapshot['observed_utc'],'events':2,'all_original_attempt1':'COMPLETED_SUCCESS','jobs':12},
    'per_event_counts':event_counts,
    'job_original_metadata_and_selected_excerpt_bindings':job_bindings,
    'numeric_DTO_independent_readback':numeric_rows,
    'private_ZIP_bytes_independently_opened':0,
    'private_full_raw_job_logs_independently_opened':0,
    'owner_original113_recheck':'Metadata-attested only by this reviewer; no independent private-byte reread.',
    'watcher_qualification':'Final child receipts/actual stdout independently match exit0 and snapshot57; parent tool exit0 is admitted owner tool-result metadata, no fabricated parent unified stdout/hash.',
    'nonacceptance_boundaries':['No qualification borrowed for newer495/27f source.','No CI runtime working-input before/after maps captured.','133 browser PASS and2467 integration PASS+2ENV SKIP are separate overlapping gates/events; not added.','6DTO describe4 logicalJob records, not6 executions or physical-process count.','Actual numerical environment_unavailable/BLOCKED/exit1 retained; HTTP409 means not published.','Failure-only diagnostic step14 skipped; real upload/readback NOT_RUN.','RealProvider/Codex/physical numeric/Broker/resource/fullM6.3/AC21/M7/source-math-teaching NOT_ACCEPTED orNOT_RUN as stated by owner.','Old35ae FAIL, unique causeUNKNOWN and previous permanent rawLOSS remain unchanged.','No absent DTO counters filled with0.'],
    'reviewer_actions':{'API_calls':0,'observer_or_product_tests':0,'external_model_calls':0,'source_or_remote_writes':0,'ZIP_or_private_runtime_or_secret_reads':0},
    'checker_sha256':sha(Path(__file__).read_bytes()),
}
(out/'READBACK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
report = '''独立只读复核完成：只读取 owner 明确准入的 2 个 outer metadata、88 个候选文本及 outer allowlist。逐文件 size/SHA、12 job capture receipt、最终 snapshot 57、指定原始行 excerpt、每次浏览器 133 个独立身份和连续 ordinal 1..133、每次 integration 2467 PASS + 2 真实环境 SKIP 均交叉校验。所有核验都保存在 READBACK.json；没有执行新 API、observer 或产品测试，也未更改产品源代码与远端。

两个原公开6671 attempt 1 在 2026-10-04T22:20:03.336053Z 已各6 job completed/success。push checkout 为6671；PR checkout 为ab37，两者官方 Git tree metadata 相同。资格只属于这两个原始事件，不属于495/27f后续源代码；未捕获 CI working-input before/after maps。

原始完整私有 log 与 ZIP 未由本次复核打开。12 完整 log 的长度/摘要/采集 exit0 与 owner113原始重检在明确候选 metadata 上交叉核验，指定 excerpt 和266 PASS结果行的内容及行摘要本次独立重算。4 ZIP 的 API digest/size、采集 receipt 与已准入6 DTO绑定独立校验 metadata，但不声称本次独立重算 ZIP bytes。最终 watcher 两个 child receipt/stdout 的 exit0、hash与snapshot57独立核验；parent tool exit0只依赖准入原 tool-result metadata，不制造 parent stdout。

6 DTO 只描述4 distinct logical Job records。全部实际 failed/environment_unavailable/BLOCKED/exit1/assertions[]，发布 HTTP409/PUBLISH_NUMERIC_REQUIRED，单块草稿 explicit published_ref:null。缺失模型字段保留 ABSENT，合成人类 APPROVED不代表数学、来源或教学验收。两个 browser job failure诊断 step14 skipped，因此真实失败 upload/readback仍NOT_RUN；真实数值、Provider/Codex、Broker/resources、整个M6.3/AC21/M7未获验收。旧35ae FAIL、原因UNKNOWN及此前永久原始Chrome LOSS原样保留。
'''
(out/'REPORT.md').write_text(report)
manifest_out = {'schema':'ExplicitIndependentReadbackFiles/v1','scope':'Only three named files; not private-directory recursion; no publication performed.','files':[]}
for name in ['verify.py','READBACK.json','REPORT.md']:
    data=(out/name).read_bytes()
    manifest_out['files'].append({'file':name,'size_bytes':len(data),'sha256':sha(data)})
(out/'FILES.json').write_text(json.dumps(manifest_out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'candidate_count':len(entries),'check_count':len(checks),'finding_count':len(findings),'findings':findings,'files':manifest_out['files']},ensure_ascii=False))
raise SystemExit(1 if findings else 0)
