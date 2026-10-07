"""Readonly original56 and pinned101 complete Python terminal evidence audit."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import time

HERE = Path(__file__).parent
BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ORIGINAL = BASE / 'm63-integrated-1564-complete-python-evidence-oct07'
FINAL_DIR = BASE / 'm63-integrated-1564-complete-python-final-readback-oct07'
HEAD = '101cee47d8e746dddac81fb6e8829069fcabff09'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def regular(base, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Invalid exact original relative path')
    result = base
    for part in p.parts:
        result /= part
        if result.is_symlink():
            raise ValueError('Unexpected evidence symlink')
    if not result.is_file():
        raise ValueError('Missing evidence regular file')
    if p.suffix.lower() in {'.png', '.zip', '.db', '.sqlite', '.sqlite3', '.key', '.pem'}:
        raise ValueError('Forbidden private artifact body in original56 manifest')
    return result


def inventory(folder):
    files = []
    for path in sorted(folder.iterdir()):
        if path.is_symlink():
            raise ValueError('Evidence inventory symlink')
        if path.is_dir():
            files.extend(inventory(path))
        elif path.is_file():
            files.append(path)
        else:
            raise ValueError('Evidence inventory nonregular path')
    return files


started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
manifest_data = regular(ORIGINAL, 'finite-originals-manifest.json').read_bytes()
manifest = json.loads(manifest_data)
expected = {row['path'] for row in manifest['files']}
actual = {str(p.relative_to(ORIGINAL)) for p in inventory(ORIGINAL)} - {'finite-originals-manifest.json'}
bindings, cache, findings = [], {}, []
for row in manifest['files']:
    path = regular(ORIGINAL, row['path'])
    data = path.read_bytes()
    binding = {'path': row['path'], 'actual_bytes': len(data), 'actual_sha256': sha(data),
               'declared_bytes': row['size'], 'declared_sha256': row['sha256'],
               'bytes_exact': len(data) == row['size'], 'sha_exact': sha(data) == row['sha256'],
               'stable_after_read': path.read_bytes() == data,
               'full_raw_stdout_public_candidate': False if row['path'] == 'complete-python/stdout.bin' else 'NOT_APPLICABLE'}
    bindings.append(binding)
    if not binding['bytes_exact'] or not binding['sha_exact'] or not binding['stable_after_read']:
        findings.append({'path': row['path'], 'kind': 'ORIGINAL_SIZE_SHA_OR_STABILITY_MISMATCH'})
    if path.suffix == '.json':
        cache[row['path']] = json.loads(data)
write('01-ALL-56-ORIGINAL-BINDINGS.json', {
    'original_directory': str(ORIGINAL), 'manifest_sha256': sha(manifest_data), 'manifest_bytes': len(manifest_data),
    'expected_paths': sorted(expected), 'actual_paths': sorted(actual), 'pathset_exact': expected == actual,
    'count': len(bindings), 'bindings': bindings,
})

baseline = cache['fixed-inputs.json']
fixed = {row['path']: row for row in baseline['entries']}
maps = {name: value for name, value in cache.items() if isinstance(value, dict) and
        'complete_exact' in value and 'entries' in value and 'count' in value}
map_rows = []
for name, value in maps.items():
    rows = {row['path']: row for row in value['entries']}
    checks = {'head101': value['head'] == HEAD, 'count1564': value['count'] == len(rows) == 1564,
        'fixed_pathset': rows.keys() == fixed.keys(), 'declared_exact': value['complete_exact'] and not value['errors'],
        'fixed_git_exact': all(rows[p]['fixed_git'] == fixed[p] for p in fixed),
        'index_mode_type_blob_stage_exact': all(rows[p]['index']['mode'] == fixed[p]['mode'] and
            rows[p]['index']['type'] == fixed[p]['type'] and rows[p]['index']['blob'] == fixed[p]['blob'] and
            str(rows[p]['index']['stage']) == '0' for p in fixed),
        'live_mode_type_blob_size_sha_exact': all(all(rows[p]['live'][k] == fixed[p][k] for k in
            ('mode', 'type', 'blob', 'size', 'sha256')) and rows[p]['matches_fixed_git'] for p in fixed),
    }
    map_rows.append({'path': name, 'bytes': regular(ORIGINAL, name).stat().st_size,
        'sha256': next(row['actual_sha256'] for row in bindings if row['path'] == name), 'checks': checks,
        'head': value['head'], 'tree': value['tree'], 'count': value['count'], 'status_recorded': value['status'],
        'allow_progress_descendant': value['allow_progress_descendant'],
        'fixed_ancestor_exit_code': value['fixed_ancestor_exit_code'],
        'canonical_nonprogress_git_entries_equal': value['canonical_nonprogress_git_entries_equal'],
        'live_fields': sorted({k for row in rows.values() for k in row['live']})})
    if not all(checks.values()):
        findings.append({'map': name, 'kind': 'PINNED_SOURCE_MAP_MISMATCH', 'checks': checks})
write('02-ALL-13-FULL-1564-SOURCE-MAP-CHECKS.json', {'source_head': HEAD, 'baseline_count': len(fixed),
    'baseline_sha256': next(row['actual_sha256'] for row in bindings if row['path'] == 'fixed-inputs.json'),
    'maps': map_rows, 'map_count': len(map_rows),
    'stat': 'inode/mtime/full stat NOT_CAPTURED_IN_THESE_MAPS',
    'current_canonical_or_source_tree_read': False,
    'later_canonical_attrs_difference': 'OUTSIDE_ORIGINAL_TEMPORAL_CAPTURE; not retroactively treated as original gate failure'})

stages = ('worktree-create', 'node-archive-reuse', 'locked-setup', 'node-version', 'complete-python')
stage_bindings = []
for stage in stages:
    command_path, receipt_path = stage + '/command.json', stage + '/receipt.json'
    command, receipt = cache[command_path], cache[receipt_path]
    stdout = regular(ORIGINAL, stage + '/stdout.bin').read_bytes()
    stderr = regular(ORIGINAL, stage + '/stderr.bin').read_bytes()
    checks = {'command_hash': receipt['command_sha256'] == sha(regular(ORIGINAL, command_path).read_bytes()),
        'stdout_binding': receipt['stdout_size'] == len(stdout) and receipt['stdout_sha256'] == sha(stdout),
        'stderr_binding': receipt['stderr_size'] == len(stderr) and receipt['stderr_sha256'] == sha(stderr),
        'original_exit0': receipt['command_exit_code'] == receipt['wrapper_exit_code'] == 0,
        'fixed_head': command['source_head'] == receipt['head'] == HEAD,
        'runner_sha': command['runner_sha256'] == receipt['runner_sha256'] == manifest['runner_sha256'],
        'no_HOME_CODEX_HOME_reassignment': 'HOME' not in command['environment'] and 'CODEX_HOME' not in command['environment'],
        'before_after_declared_exact': receipt['before_after_complete_exact'] and receipt['input_count'] == 1564,
        'before_after_rows_exact': cache[stage + '/before.json']['entries'] == cache[stage + '/after.json']['entries']}
    stage_bindings.append({'stage': stage, 'argv': command['argv'], 'cwd': command['cwd'],
        'actual_command_exit': receipt['command_exit_code'], 'actual_wrapper_exit': receipt['wrapper_exit_code'],
        'stdout_bytes': len(stdout), 'stdout_sha256': sha(stdout), 'stderr_bytes': len(stderr), 'stderr_sha256': sha(stderr),
        'elapsed_wrapper_seconds': receipt['elapsed_seconds'], 'checks': checks})
    if not all(checks.values()):
        findings.append({'stage': stage, 'kind': 'ORIGINAL_COMMAND_STREAM_RECEIPT_MISMATCH', 'checks': checks})
write('03-FIVE-ORIGINAL-COMMAND-STREAM-RECEIPT-BINDINGS.json', {'stages': stage_bindings})

# Hash and size binding above precede selection; no full stdout copy is made.
stdout_path = regular(ORIGINAL, 'complete-python/stdout.bin')
stdout_raw = stdout_path.read_bytes()
selected = []
for number, line in enumerate(stdout_raw.decode().splitlines(), 1):
    if re.fullmatch(r'collected \d+ items', line.strip()) or re.fullmatch(r'=+ \d+ passed, \d+ skipped, \d+ warnings in [0-9.]+s \([0-9:]+\) =+', line.strip()) or line.startswith('SKIPPED [1] tests/integration/test_authoring_numeric_runtime.py:') or line.startswith('SKIPPED [1] tests/integration/test_restore_numeric_actual_runtime.py:'):
        selected.append({'original_file': 'complete-python/stdout.bin', 'original_sha256': sha(stdout_raw),
                         'original_bytes': len(stdout_raw), 'line_number': number, 'text': line,
                         'line_sha256_utf8_no_newline': sha(line.encode())})
write('SAFE-ORIGINAL-LINES.json', {'lines': selected, 'full_original_stdout_included': False,
    'scope': 'Exact collection/footer/two original numeric ENV skip lines only; no fixture/AuthCase/CSRF/error body'})
footer = next(row['text'] for row in selected if ' passed, ' in row['text'])
match = re.search(r'(\d+) passed, (\d+) skipped, (\d+) warnings in ([0-9.]+)s', footer)
actual_counts = {'passed': int(match[1]), 'failed': 0, 'skipped': int(match[2]), 'warnings': int(match[3]), 'errors': 0, 'xfailed': 0, 'xpassed': 0}
actual_collected = int(re.search(r'collected (\d+) items', next(row['text'] for row in selected if 'collected ' in row['text']))[1])
skips = [row['text'] for row in selected if row['text'].startswith('SKIPPED')]

final_data = regular(FINAL_DIR, 'FINAL.json').read_bytes()
final_manifest_data = regular(FINAL_DIR, 'manifest.json').read_bytes()
final, final_manifest = json.loads(final_data), json.loads(final_manifest_data)
result, full_receipt = cache['RESULT.json'], cache['complete-python/receipt.json']
final_checks = {
    'given_original_manifest_sha': sha(manifest_data) == 'dfae73881cddf96d636f36458f0c6971e76b2089f9ce6b5df33f81c9a8cb4ba2',
    'given_FINAL_sha': sha(final_data) == '363a05abc90fbe512d7f5905d12dea29d5081dbf796e39b304604ed9c5e14b17',
    'given_final_manifest_sha': sha(final_manifest_data) == '79527851f6f1b0f729a7c82bca523565cca5c64c76ccf249a8d7d649ef3c96d4',
    'final_manifest_binding': final_manifest['count'] == 1 and final_manifest['files'] == [{'path': 'FINAL.json', 'size': len(final_data), 'sha256': sha(final_data)}],
    'counts_from_original_stdout_exact': final['counts'] == result['counts'] == actual_counts,
    'collected_from_original_stdout_exact': final['collected'] == result['collected'] == actual_collected == 4589,
    'original_counts_4587P_2skip_3warn': actual_counts['passed'] == 4587 and actual_counts['skipped'] == 2 and actual_counts['warnings'] == 3,
    'numeric_skips_ENV_not_PASS': len(skips) == 2 and skips == final['original_skip_reasons'] == result['original_skip_reasons'] and
        all('BLOCKED_ENVIRONMENT' in line for line in skips) and final['numeric_acceptance'] == 'BLOCKED_ENVIRONMENT',
    'original_full_argv_no_filters_retry': cache['complete-python/command.json']['argv'] == ['uv', 'run', '--frozen', '--offline', 'pytest'] and
        cache['complete-python/command.json']['retry'] == 0 and final['full_started_count'] == result['full_started_count'] == 1,
    'uv_wrapper_actual0': full_receipt['command_exit_code'] == full_receipt['wrapper_exit_code'] == final['actual_command_exit_code'] == final['wrapper_exit_code'] == 0,
    'FINAL_captured_source_and_canon_closure': final['final_source1564_exact'] and final['final_canonical1564_exact'] and
        final['final_source_head'] == final['final_canonical_head'] == HEAD and final['canonical_fixed_ancestor_exit_code'] == 0 and
        final['canonical_nonprogress_git_entries_equal'] and final['final_source_count'] == 1564,
    'phase_pending_result_preserved': result['final_canonical_closure'] == 'PENDING_FREEZE' and 'phase_RESULT_PENDING_FREEZE_is_preserved' in final,
    'network_not_zero_claim': final['public_dependency_installer_network_used'] and result['setup_public_network_permitted_and_used'] and result['no_zero_network_claim'],
    'no_host_production_M7_claim': final['no_HOSTproof_or_actual_production_turn_or_M7_claim'] and result['no_HOSTproof_or_production_turn_or_M7_acceptance_claim'],
    'prior_results_separate': final['old079_failure_and_8bd_scoped6P_remain_independent'] and result['old079_failure_and_8bd_scoped6P_kept_separate'],
}
for name, passed in final_checks.items():
    if not passed:
        findings.append({'final_check': name})
write('04-FINAL-AND-ORIGINAL-RESULT-CROSSCHECK.json', {'actual_collected': actual_collected, 'actual_counts': actual_counts,
    'pytest_footer_seconds': float(match[4]), 'actual_wrapper_elapsed_seconds': full_receipt['elapsed_seconds'],
    'checks': final_checks, 'captured_FINAL': final,
    'final_manifest_sha256': sha(final_manifest_data), 'FINAL_sha256': sha(final_data),
    'current_canonical_read': False, 'complete_raw_stdout_candidate': False})
if expected != actual or len(expected) != len(bindings) != 56 or len(maps) != 13:
    findings.append({'kind': 'ORIGINAL_PATHSET_OR_MAP_COUNT_MISMATCH'})
review = {'started_utc': started, 'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'fixed_head': HEAD, 'original56_hash_size_pathset': 'EXACT' if not findings else 'SEE_RECORDED_FINDINGS',
    'originals': len(bindings), 'full_source_maps': len(maps), 'source_inputs': len(fixed),
    'actual_collected': actual_collected, 'actual_counts': actual_counts, 'pytest_footer_seconds': float(match[4]),
    'actual_command_exit': full_receipt['command_exit_code'], 'actual_wrapper_exit': full_receipt['wrapper_exit_code'],
    'numeric_acceptance': 'BLOCKED_ENVIRONMENT; two skips are not numeric PASS', 'selected_original_line_count': len(selected),
    'findings': findings, 'Standards_new_blocking': len(findings), 'Spec_new_blocking': len(findings),
    'stat': 'NOT_CAPTURED', 'host_zero_network': 'NOT_PROVEN; public installer network used',
    'original_RESULT_PENDING_FREEZE': 'RETAINED; later FINAL independently captured closure',
    'current_canonical_later_attrs': 'NOT_READ; not used to relabel pinned101 gate',
    'old079_FAIL_8bd6P_native133P': 'SEPARATE_NONADDITIVE_RECORDS', 'whole_M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED',
    'real_provider_Codex_turn_host_probes_tests_remote_canonical_mutation': 'NOT_RUN_BY_THIS_REVIEW',
    'HOME_CODEX_HOME_overrides': False, 'full_private_raw_stdout_public_copy': False}
write('REVIEW.json', review)
print(json.dumps(review), flush=True)
assert not findings, 'All original audit facts/streams saved before status assertion'
