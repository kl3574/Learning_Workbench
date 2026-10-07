"""Read only the named eighteenth-file native publication packet and its sixteen declared origins."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import math
import re
import time

HERE = Path(__file__).parent
BASE = Path('$HOME/.cache/learning-workbench-acceptance')
REPO = BASE / 'm62-public-safe-oct02'
PACKAGE = 'progress/evidence/2026-10-07/M6.3-current101cee-original-full133-native-terminal-pass-independent-raw-mutations-restored'
FOLDER = REPO / PACKAGE
HEAD = '101cee47d8e746dddac81fb6e8829069fcabff09'
ORIGINS = {'m63-integrated-1564-full-native-evidence-oct07', 'm63-current101-full-native-root-admission-oct07'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def checked(base, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Invalid finite relative path')
    result = base
    for part in path.parts:
        result /= part
        if result.is_symlink():
            raise ValueError('Finite symlink not admitted')
    if not result.is_file():
        raise ValueError('Missing finite regular file')
    return result


def inventory(folder):
    result = []
    for p in sorted(folder.iterdir()):
        if p.is_symlink():
            raise ValueError('Finite inventory symlink not admitted')
        if p.is_dir():
            result.extend(inventory(p))
        elif p.is_file():
            result.append(p)
        else:
            raise ValueError('Finite inventory nonregular path')
    return result


started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
manifest_bytes = checked(FOLDER, 'manifest.json').read_bytes()
manifest = json.loads(manifest_bytes)
entries, parsed, findings = [], {}, []
home_count = runner_count = 0
for e in manifest['entries']:
    path = checked(FOLDER, e['file'])
    if path.suffix not in ('.json', '.py'):
        raise ValueError('Unexpected archive/image/runtime body in native finite packet')
    published = path.read_bytes()
    row = {'file': e['file'], 'published_bytes': len(published), 'published_sha256': sha(published),
           'published_sha_exact': sha(published) == e['published_sha256'], 'transformation': e['transformation']}
    if 'source_package' in e:
        if e['source_package'] not in ORIGINS:
            raise ValueError('Origin outside the two explicitly authorized native evidence packages')
        raw = checked(BASE / e['source_package'], e['source_relative']).read_bytes()
        h, r = raw.count(b'$HOME'), raw.count(b'$RUNNER_HOME')
        home_count += h; runner_count += r
        expected = raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
        row.update({'source_package': e['source_package'], 'source_relative': e['source_relative'],
                    'raw_bytes': len(raw), 'raw_sha256': sha(raw), 'raw_sha_exact': sha(raw) == e['raw_sha256'],
                    'published_bytes_exact': len(published) == len(expected), 'sole_prefix_bytes_exact': expected == published,
                    'transformation_exact': e['transformation'] == ('none' if raw == expected else 'exact personal-home/runner prefix replacement only'),
                    'home_occurrences': h, 'runner_occurrences': r})
        if not all(row[k] for k in ('published_sha_exact', 'raw_sha_exact', 'published_bytes_exact', 'sole_prefix_bytes_exact', 'transformation_exact')):
            findings.append({'file': e['file'], 'kind': 'ORIGIN_PREFIX_MISMATCH'})
    else:
        row['manual_source'] = e['file'] == 'REPORT.json' and e['transformation'] == 'new scoped summary'
        if not row['manual_source'] or not row['published_sha_exact']:
            findings.append({'file': e['file'], 'kind': 'MANUAL_SOURCE_MISMATCH'})
    if path.suffix == '.json':
        parsed[e['file']] = json.loads(published)
    entries.append(row)
actual = sorted(str(p.relative_to(FOLDER)) for p in inventory(FOLDER))
expected_files = sorted(['manifest.json'] + [e['file'] for e in manifest['entries']])
write('01-ALL-16-ORIGIN-PREFIX-BINDINGS.json', {'package': PACKAGE, 'manifest_sha256': sha(manifest_bytes),
    'manifest_bytes': len(manifest_bytes), 'entries': entries, 'actual_home_occurrences': home_count,
    'actual_runner_occurrences': runner_count, 'expected_files': expected_files, 'actual_files': actual,
    'inventory_exact': actual == expected_files, 'physical_file_count': len(actual)})

prefix = 'owner-safe/safe-candidates/'
maps = {name: parsed[prefix + name + '-SOURCE-MAP.json'] for name in
        ('before-setup', 'before-native', 'raw-after-native', 'after-guard-restore')}
baseline = {r['path']: r for r in maps['before-setup']['source_files']}
map_checks = {}
for name, m in maps.items():
    rows = {r['path']: r for r in m['source_files']}
    map_checks[name] = {'head': m['head'], 'source_count': m['source_count'], 'row_count': len(rows),
        'same_paths': rows.keys() == baseline.keys(),
        'git_exact': all(rows[p]['git'] == baseline[p]['git'] for p in baseline),
        'index_exact': all(rows[p]['index'] == baseline[p]['index'] for p in baseline),
        'declared_git_index_deltas': m['git_index_deltas'],
        'actual_row_differences': sorted(p for p in baseline if rows[p] != baseline[p]),
        'declared_live_deltas': m['git_live_deltas'],
        'live_stat_fields': sorted({k for r in rows.values() for k in r['live']})}
raw_rows = {r['path']: r for r in maps['raw-after-native']['source_files']}
restored_rows = {r['path']: r for r in maps['after-guard-restore']['source_files']}
changed = map_checks['raw-after-native']['actual_row_differences']
restore = parsed[prefix + '22-TRACKED-NATIVE-ARTIFACT-RESTORE.json']
mutations = []
for item in restore['mutations']:
    p = item['path']
    mutations.append({'path': p, 'raw_live': raw_rows[p]['live'], 'baseline_live': baseline[p]['live'],
        'restored_live': restored_rows[p]['live'],
        'raw_sha_bound': raw_rows[p]['live']['sha256'] == item['actual_sha256'],
        'raw_bytes_bound': raw_rows[p]['live']['bytes'] == item['actual_bytes'],
        'restored_sha_bound': baseline[p]['live']['sha256'] == item['restored_sha256'],
        'actual_restore_exact': restored_rows[p] == baseline[p],
        'private_artifact_read_or_copied': False})
write('02-FOUR-FULL-MAP-AND-FIVE-MUTATION-READBACK.json', {'maps': map_checks, 'mutations': mutations,
    'raw_mutation_count': len(changed), 'restore_declared_count': restore['actual_tracked_mutation_count'],
    'all_four_git_index_exact': all(m['git_exact'] and m['index_exact'] and not m['declared_git_index_deltas'] for m in map_checks.values()),
    'setup_before_restore_rows_exact': maps['before-setup']['source_files'] == maps['before-native']['source_files'] == maps['after-guard-restore']['source_files'],
    'raw_after_exact': False, 'restored_exact_scope': 'mode/type/blob/bytes/SHA fields actually present; inode/mtime not recorded in these maps',
    'private_images_metrics_DB_profile_body_access': 'NOT_RUN; only supplied source-map/hash metadata read'})

allowed_routes = {'/api/v1/assessments/:id/attempts', '/api/v1/attempts/:id', '/api/v1/attempts/:id/regrade',
    '/api/v1/attempts/:id/responses', '/api/v1/attempts/:id/result', '/api/v1/attempts/:id/submit',
    '/api/v1/blocks/:id', '/api/v1/blocks/:id/body', '/api/v1/courses/:id', '/api/v1/imports',
    '/api/v1/imports/:id', '/api/v1/imports/:id/commit', '/api/v1/jobs/:id', '/api/v1/lessons/:id',
    '/api/v1/session', '/api/v1/session/role', '/api/v1/workbench/session'}
timings = []
for name, event_key, phases_count, event_count in (
        ('review-history-setup-helper-timing.json', 'polls', 39, 4), ('review-history-timing.json', 'http', 43, 321)):
    t = parsed[prefix + name]
    events = t[event_key]
    keys_allowed = {'sequence', 'elapsed_ms', 'event', 'method', 'route', 'status', 'caller', 'request_elapsed_ms'}
    numeric_fields_valid = all(type(row['sequence']) is int and row['sequence'] > 0 and
        isinstance(row['elapsed_ms'], (int, float)) and math.isfinite(row['elapsed_ms']) and row['elapsed_ms'] >= 0 for row in t['phases'] + events)
    checks = {'phase_count_exact': len(t['phases']) == phases_count, 'event_count_exact': len(events) == event_count,
        'budget_retry_unchanged': t['observed_timeout_ms'] == 30000 and t['retry'] == 0,
        'finite_caps': len(t['phases']) <= t['limits']['phases'] and len(events) <= t['limits'][event_key],
        'zero_dropped': not any(t['dropped'].values()),
        'phase_keys_closed': all(set(row) == {'sequence', 'elapsed_ms', 'stage'} for row in t['phases']),
        'event_keys_closed': all(set(row) <= keys_allowed for row in events),
        'stage_labels_only': all(re.fullmatch(r'[a-z0-9-]+', row['stage']) for row in t['phases']),
        'routes_static_closed': all(row['route'] in allowed_routes for row in events),
        'numeric_metadata_finite': numeric_fields_valid,
        'http_values_closed': all(row['method'] in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'} and
            ('status' not in row or type(row['status']) is int and 100 <= row['status'] <= 599) and
            ('event' not in row or row['event'] in {'request', 'response', 'requestfailed'}) for row in events),
        'finalizer_boundary': t['phases'][-1]['stage'] == 'body-finally',
        'contains_no_query_fragment_or_absolute_url': all('?' not in row['route'] and '#' not in row['route'] and '://' not in row['route'] for row in events)}
    if event_key == 'polls':
        checks['poll_routes_callers_fixed'] = all(row['route'] == '/api/v1/attempts/:id/result' and
            row['caller'] in {'initial-grade-poll', 'manual-grade-poll'} for row in events)
    timings.append({'artifact': name, 'phase_count': len(t['phases']), 'event_count': len(events),
        'checks': checks, 'unique_stages': sorted({row['stage'] for row in t['phases']}),
        'unique_routes': sorted({row['route'] for row in events}), 'last_phase': t['phases'][-1], 'scope': t['scope']})
    if not all(checks.values()):
        findings.append({'artifact': name, 'failed_checks': [key for key, value in checks.items() if not value]})
write('03-TIMING-POSITIVE-METADATA-READBACK.json', {'timings': timings,
    'privacy_scope': 'Closed event keys and fixed static routes/callers/status/numeric durations; no query/header/body/JSON/auth/form/DOM/private ID values. Read-only category admission, not runtime fault qualification.'})

owner = parsed[prefix + 'REPORT.json']
summary = parsed['REPORT.json']
root = parsed['root-independent/ROOT-READBACK.json']
safe_lines = parsed[prefix + 'SAFE-ORIGINAL-LINES.json']
command_summary = parsed[prefix + 'COMMAND-RECEIPT-SUMMARY.json']
labels = {row['label']: row['exit_code'] for row in command_summary}
ci = owner['original_ci_separate']
scope_checks = {
    'local_source_101': owner['source_commit'] == summary['source'] == root['source'] == HEAD,
    'local_native_133_once': owner['full_native']['actual_original_counts'] == {'passed': 133, 'failed': 0, 'skipped': 0, 'did_not_run': 0, 'flaky': 0} and
        owner['full_native']['exit_code'] == 0 and owner['full_native']['attempt_count'] == 1 and labels['20-full-native'] == 0,
    '166_admitted_lines_133_success': len(safe_lines) == 166 and sum(bool(re.match(r'^\s*✓\s+\d+\s', r['text'])) for r in safe_lines) == 133,
    'old_original_PR_failure_separate': ci['pr_run'] == 37632662238 and ci['browser_job'] == 112830674946 and
        ci['actual_original_result'] == '1 FAIL /132 PASS (39.9m)' and ci['cause'] == 'UNKNOWN' and not ci['repair_claim'] and
        not ci['current_local_pass_replaces_original_ci_failure'],
    'original_metadata_order_failures_retained': labels['22-restore-native-artifacts'] == labels['23-after-restore-map'] == 1 and
        labels['22b-continue-restoration'] == labels['23b-continue-post-map'] == 0,
    'no_M63_acceptance': summary['M63'] == root['M63'] == 'NOT_ACCEPTED' and owner['scope_boundary']['M6_3_or_models_acceptance'] == 'NOT_ESTABLISHED',
    'real_provider_codex_not_run': owner['scope_boundary']['real_provider'] == owner['scope_boundary']['real_codex'] == 'NOT_RUN',
    'images_DB_profiles_raw_logs_excluded': owner['scope_boundary']['raw_logs_payloads_screenshots_runtime_DB_profiles_ZIPs'] == 'PRIVATE_EXCLUDED_FROM_SAFE_CANDIDATES',
    'manual_summary_scope_distinct': summary['old_PR_failure'] == root['old_PR_failure'] and summary['source_maps'] == root['source_maps'] and summary['timings'] == root['timings'],
}
for name, passed in scope_checks.items():
    if not passed:
        findings.append({'scope_check': name})
for name, m in map_checks.items():
    if m['head'] != HEAD or m['source_count'] != m['row_count'] != 1564 or not m['same_paths'] or not m['git_exact'] or not m['index_exact']:
        findings.append({'source_map': name, 'kind': 'SOURCE_MAP_SCOPE_MISMATCH'})
if actual != expected_files or len(actual) != 18 or len(entries) != 17 or len(changed) != 5 or set(changed) != {m['path'] for m in mutations}:
    findings.append({'kind': 'FINITE_OR_MUTATION_COUNT_MISMATCH'})
if not all(all(m[key] for key in ('raw_sha_bound', 'raw_bytes_bound', 'restored_sha_bound', 'actual_restore_exact')) for m in mutations):
    findings.append({'kind': 'MUTATION_RESTORE_BINDING_MISMATCH'})
write('04-MANUAL-SCOPE-AND-SOURCE-READBACK.json', {'scope_checks': scope_checks, 'manual_summary': summary,
    'included_command_summary_entries': len(command_summary), 'root_claimed_original_quartets': root['exact_original_quartets'],
    'qualification_scope': 'This independent publication review binds16 included origins, not all159 root originals or23 private command quartets. Root159/23 admission is a separately identified source record; no private artifact/log re-read here.'})
result = {'started_utc': started, 'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'package': PACKAGE, 'origins': 16, 'manual_summaries': 1, 'physical_files': 18,
    'literal_prefix_occurrences': {'$HOME': home_count, '$RUNNER_HOME': runner_count},
    'findings': findings, 'Standards_new_blocking': len(findings), 'Spec_new_blocking': len(findings),
    'raw_source_live_changes': 5, 'restored_1564_row_exact': maps['before-setup']['source_files'] == maps['before-native']['source_files'] == maps['after-guard-restore']['source_files'],
    'source_maps_inode_mtime': 'NOT_CAPTURED_IN_THESE_FOUR_MAPS',
    'old079_PR_1F132P': 'RETAINED_SEPARATE_UNKNOWN_CAUSE', 'current101_local133P': 'SOURCE_RECORD_ONLY; original tests not rerun by this owner',
    'private_logs_artifacts_images_DB_profiles_read_or_copied': False, 'original_scripts_imported_executed': False,
    'canonical_remote_tests_model_hostprobes': 'NOT_RUN_OR_MUTATED', 'HOME_CODEX_HOME_override': False,
    'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED', 'production_runtime_InputProof': 'NOT_QUALIFIED'}
write('REVIEW.json', result)
print(json.dumps(result), flush=True)
assert not findings, 'All original read audit facts preserved before assertion'
