"""Read only the twelve explicitly enumerated finite progress packages and declared origins."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import sys
import time

HERE = Path(__file__).parent
REPO = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
BASE = Path('$HOME/.cache/learning-workbench-acceptance')
HELPER = BASE / 'm63-public079a008-progress-record-oct07/package-helper.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def checked_path(base, relative):
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts:
        raise ValueError('Invalid relative finite path')
    target = base
    for part in parts.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError('Finite path symlink not admitted')
    if not target.is_file():
        raise ValueError('Finite path is not an existing regular file')
    return target


def inventory(directory):
    files = []
    for child in sorted(directory.iterdir()):
        if child.is_symlink():
            raise ValueError('Published finite inventory symlink not admitted')
        if child.is_dir():
            files.extend(inventory(child))
        elif child.is_file():
            files.append(child)
        else:
            raise ValueError('Published finite inventory has nonregular object')
    return files


def category(path):
    name = path.name.lower()
    if path.suffix in ('.py', '.patch'):
        return 'PUBLIC_CODE_OR_SOURCE_DIFF'
    if path.suffix == '.json':
        return 'DECLARED_FINITE_METADATA'
    if path.suffix == '.md':
        return 'SCOPED_REPORT_OR_MANAGED_BODY'
    if 'sha256sum' in name:
        return 'ORIGINAL_HASH_METADATA'
    return 'SAFE_COMMAND_STREAM_OR_ADMITTED_EXCERPT'


def path_sensitive(relative):
    p = PurePosixPath(relative)
    parts = set(part.lower() for part in p.parts)
    return (p.suffix.lower() in ('.zip', '.db', '.sqlite', '.sqlite3', '.png', '.key', '.pem') or
            bool(parts & {'node_modules', '.venv', 'profile', 'profiles', 'browser-profile', 'runtime',
                          'credentials', 'secrets', 'raw-api', 'rawapi'}) or
            p.name.lower() in {'storage-state.json', 'auth.json', '.env', 'config.toml'})


def sensitive_content(data, suffix):
    # Bounded admission checks on declared publication bytes; no host/security probing.
    hits = []
    if data.startswith((b'PK\x03\x04', b'SQLite format 3\x00', b'\x89PNG\r\n\x1a\n')):
        hits.append('FORBIDDEN_ARCHIVE_DB_OR_IMAGE_MAGIC')
    if b'\x00' in data:
        hits.append('UNEXPECTED_NUL_BINARY_BODY')
    if suffix not in ('.py', '.patch') and re.search(rb'\b(?:AuthCase|Case)\(', data):
        hits.append('POSSIBLE_AUTH_CASE_REPR')
    if re.search(rb'(?:sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)', data):
        hits.append('POSSIBLE_SECRET_BODY')
    if suffix == '.json':
        parsed = json.loads(data)
        secret_keys = {'csrf_token', 'csrf_secret', 'session_csrf', 'authorization', 'api_key',
                       'access_token', 'refresh_token', 'cookie', 'cookies', 'password'}
        safe_labels = {'NONE', 'NOT_RUN', 'NOT_CAPTURED', 'EXCLUDED', 'PRIVATE_EXCLUDED', 'FALSE', 'DISABLED'}
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.lower() in secret_keys and isinstance(item, str) and item and item.upper() not in safe_labels:
                        hits.append('POSSIBLE_PRIVATE_TOKEN_VALUE_IN_JSON_KEY:' + key)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(parsed)
    return sorted(set(hits))


started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
capture = json.loads((HERE / '08-EXPANDED-12-PACKAGE-MANIFESTS-READBACK.json').read_text())
package_rows = capture['rows']
helper_data = HELPER.read_bytes()
helper_rule = b"raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')"
write('09-PUBLISHER-RULE-READBACK.json', {
    'path': str(HELPER), 'bytes': len(helper_data), 'sha256': sha(helper_data),
    'literal_rule_present': helper_rule in helper_data,
    'rules': [{'raw_prefix': '$HOME', 'published_prefix': '$HOME'},
              {'raw_prefix': '$RUNNER_HOME', 'published_prefix': '$RUNNER_HOME'}],
    'rule_semantics': 'Literal replacement of all occurrences; no boundary, decode/reencode, formatting or other transformation',
    'helper_executed_or_imported': False,
    'active_CURRENT_state_read': False,
})

findings, binding_rows, package_checks, summaries, files = [], [], [], [], []
home_occurrences = runner_occurrences = 0
for package in package_rows:
    relative = package['package']
    folder = REPO / relative
    if not relative.startswith('progress/evidence/2026-10-07/') or relative not in capture['untracked_package_paths']:
        findings.append({'package': relative, 'kind': 'UNENUMERATED_PACKAGE'})
        continue
    manifest_path = checked_path(folder, 'manifest.json')
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    expected = {'manifest.json'} | {entry['file'] for entry in manifest['entries']}
    actual = {str(path.relative_to(folder)) for path in inventory(folder)}
    duplicates = len(manifest['entries']) != len({entry['file'] for entry in manifest['entries']})
    package_checks.append({'package': relative, 'manifest_bytes': len(manifest_data), 'manifest_sha256': sha(manifest_data),
                           'captured_manifest_sha256': package['manifest_sha256'],
                           'manifest_unchanged_since_initial_read': sha(manifest_data) == package['manifest_sha256'],
                           'manifest_entry_count': len(manifest['entries']), 'physical_file_count': len(actual),
                           'unexpected_files': sorted(actual - expected), 'missing_files': sorted(expected - actual),
                           'duplicate_entries': duplicates})
    if actual != expected or duplicates or sha(manifest_data) != package['manifest_sha256']:
        findings.append({'package': relative, 'kind': 'FINITE_INVENTORY_OR_MANIFEST_MISMATCH'})
    files.append({'package': relative, 'file': 'manifest.json', 'published_bytes': len(manifest_data),
                  'published_sha256': sha(manifest_data), 'category': 'PUBLICATION_PROVENANCE_MANIFEST',
                  'source_kind': 'MANUAL_PUBLICATION_MANIFEST; not claimed as an owner raw file'})
    for entry in manifest['entries']:
        name = entry['file']
        row = {'package': relative, 'file': name, 'declared_transformation': entry['transformation']}
        if path_sensitive(name) or path_sensitive(entry.get('source_relative', '')):
            findings.append({'package': relative, 'file': name, 'kind': 'FORBIDDEN_FINITE_PATH; source body not read'})
            row['source_read'] = 'NOT_RUN_FORBIDDEN_PATH'
            binding_rows.append(row)
            continue
        target = checked_path(folder, name)
        published = target.read_bytes()
        hits = sensitive_content(published, target.suffix)
        row.update({'published_bytes': len(published), 'published_sha256': sha(published),
                    'declared_published_sha256': entry['published_sha256'],
                    'published_hash_exact': sha(published) == entry['published_sha256'],
                    'category': category(target), 'sensitive_admission_hits': hits})
        if hits:
            findings.append({'package': relative, 'file': name, 'kind': 'SENSITIVE_CONTENT_ADMISSION', 'categories': hits})
            row['source_read'] = 'NOT_RUN_PENDING_PRIVACY_REVIEW'
            binding_rows.append(row)
            continue
        if 'source_package' in entry:
            source_name = entry['source_package']
            if PurePosixPath(source_name).parts != (source_name,):
                raise ValueError('Source package must be the exact declared single directory name')
            source = checked_path(BASE / source_name, entry['source_relative'])
            raw = source.read_bytes()
            h, r = raw.count(b'$HOME'), raw.count(b'$RUNNER_HOME')
            safe = raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
            home_occurrences += h
            runner_occurrences += r
            expected_transformation = 'exact personal-home/runner prefix replacement only' if raw != safe else 'none'
            row.update({'source_kind': 'EXACT_DECLARED_OWNER_FILE', 'source_package': source_name,
                        'source_relative': entry['source_relative'], 'raw_bytes': len(raw), 'raw_sha256': sha(raw),
                        'declared_raw_sha256': entry['raw_sha256'], 'raw_hash_exact': sha(raw) == entry['raw_sha256'],
                        'expected_published_bytes': len(safe), 'published_bytes_exact': len(safe) == len(published),
                        'allowed_transformation_bytes_exact': safe == published,
                        'transformation_description_exact': entry['transformation'] == expected_transformation,
                        'home_prefix_occurrences': h, 'runner_prefix_occurrences': r,
                        'raw_source_stable_after_read': source.read_bytes() == raw})
            if not all(row[key] for key in ('raw_hash_exact', 'published_hash_exact', 'published_bytes_exact',
                                            'allowed_transformation_bytes_exact', 'transformation_description_exact',
                                            'raw_source_stable_after_read')):
                findings.append({'package': relative, 'file': name, 'kind': 'ORIGIN_OR_PREFIX_BINDING_MISMATCH'})
        else:
            row.update({'source_kind': 'MANUAL_SCOPED_SUMMARY', 'source_read': 'NOT_APPLICABLE_NO_RAW_OWNER_CLAIM',
                        'manual_summary_admitted': name == 'REPORT.json' and entry['transformation'] == 'new scoped summary'})
            if not row['manual_summary_admitted'] or not row['published_hash_exact']:
                findings.append({'package': relative, 'file': name, 'kind': 'UNDECLARED_MANUAL_SOURCE'})
            summaries.append({'package': relative, 'file': name, 'sha256': sha(published), 'bytes': len(published),
                              'summary': json.loads(published),
                              'review_basis': 'Explicitly manual scoped summary; report is not passed off as raw source or a new runtime/provider/CI qualification'})
        row['published_stable_after_read'] = target.read_bytes() == published
        if not row['published_stable_after_read']:
            findings.append({'package': relative, 'file': name, 'kind': 'PUBLISHED_BYTES_CHANGED_DURING_READ'})
        binding_rows.append(row)
        files.append({'package': relative, **{key: row[key] for key in ('file', 'published_bytes', 'published_sha256', 'category', 'source_kind')}})

result = {
    'started_utc': started, 'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'package_count': len(package_checks), 'source_entry_count': sum(row.get('source_kind') == 'EXACT_DECLARED_OWNER_FILE' for row in binding_rows),
    'manual_summary_count': len(summaries), 'manifest_entry_count': len(binding_rows), 'physical_finite_file_count': len(files),
    'unique_source_files': len({(row['source_package'], row['source_relative']) for row in binding_rows if row.get('source_package')}),
    'actual_literal_prefix_occurrences': {'$HOME': home_occurrences, '$RUNNER_HOME': runner_occurrences},
    'publication_finding_count': len(findings), 'findings': findings,
    'scope': 'Finite publication origin/bytes/privacy-category review only; no source implementation or whole-platform acceptance',
    'HOME_override_in_this_audit': False, 'CODEX_HOME_override_in_this_audit': False,
    'models_tests_remote_hostprobes': 'NOT_RUN', 'CURRENT_state': 'NOT_READ',
    'scanner_substitution_for_manual_admission': False, 'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED',
}
write('10-ALL-370-ENTRY-ORIGIN-PREFIX-BINDINGS.json', {'result': result, 'entries': binding_rows})
write('11-ALL-382-FINITE-FILE-INVENTORY.json', {'files': files, 'packages': package_checks})
write('12-MANUAL-SUMMARY-SCOPE-READBACK.json', {'summaries': summaries})
write('13-ACTUAL-AUDIT-RESULT.json', result)
print(json.dumps(result), flush=True)
if len(findings):
    sys.exit(1)
assert helper_rule in helper_data, 'Original helper rule mismatch captured'
assert len(package_checks) == 12 and len(binding_rows) == 370 and len(files) == 382
assert result['source_entry_count'] == 358 and result['manual_summary_count'] == 12
