"""Package only already-read original metadata and four bounded stdout lines."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ORIGIN = Path('$HOME/.cache/learning-workbench-acceptance/m63-integrated-1564-complete-python-evidence-oct07')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(name, raw):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)

def put_json(name, value):
    put(name, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode())

bindings = json.loads((HERE / '01-ALL-56-ORIGINAL-BINDINGS.json').read_bytes())
maps = json.loads((HERE / '02-ALL-13-FULL-1564-SOURCE-MAP-CHECKS.json').read_bytes())
review = json.loads((HERE / 'REVIEW.json').read_bytes())
assert bindings['count'] == 56
assert len(bindings['bindings']) == 56
assert len(bindings['expected_paths']) == 56
assert len(bindings['actual_paths']) == 56
assert bindings['expected_paths'] == bindings['actual_paths']
assert maps['map_count'] == 13 and len(maps['maps']) == 13
assert maps['baseline_count'] == 1564
assert review['findings'] == []
assert review['Standards_new_blocking'] == review['Spec_new_blocking'] == 0
assert review['actual_counts'] == {'errors': 0, 'failed': 0, 'passed': 4587, 'skipped': 2, 'warnings': 3, 'xfailed': 0, 'xpassed': 0}
by_path = {entry['path']: entry for entry in bindings['bindings']}

# Copies are metadata only: baseline, original full-gate maps and final closures,
# plus the five original receipts. Full raw stdout is deliberately not copied.
selected = ['fixed-inputs.json', 'complete-python/before.json',
            'complete-python/after.json', 'final-new-worktree-inputs.json',
            'final-canonical-inputs.json']
selected += [stage + '/receipt.json' for stage in
             ['worktree-create', 'node-archive-reuse', 'locked-setup',
              'node-version', 'complete-python']]
copies = []
for relative in selected:
    data = (ORIGIN / relative).read_bytes()
    binding = by_path[relative]
    assert len(data) == binding['actual_bytes']
    assert sha(data) == binding['actual_sha256']
    destination = 'safe-originals/' + relative
    put(destination, data)
    copies.append({'path': destination, 'source_package': str(ORIGIN),
                   'source_relative': relative, 'bytes': len(data),
                   'sha256': sha(data), 'transformation': 'none',
                   'category': 'original full source map' if relative in selected[:5]
                               else 'original command receipt'})
put_json('07-SAFE-ORIGINAL-COPY-BINDINGS.json', {'count': len(copies), 'entries': copies})
put_json('06-AUDIT-ACTUAL-TOOL-RECEIPT.json', {
    'tool': 'exec_command', 'actual_chunk_id': 'b7cc0f',
    'actual_exit_code': 0, 'execution': 'independent evidence audit only',
    'script': 'audit_complete_python.py',
    'script_sha256': sha((HERE / 'audit_complete_python.py').read_bytes()),
    'shell_command_separate_capture': 'NOT_CAPTURED; no reconstructed exact shell text asserted',
    'stdout_file': '05-AUDIT.stdout',
    'stdout_bytes': len((HERE / '05-AUDIT.stdout').read_bytes()),
    'stdout_sha256': sha((HERE / '05-AUDIT.stdout').read_bytes()),
    'stderr_file': '05-AUDIT.stderr',
    'stderr_bytes': len((HERE / '05-AUDIT.stderr').read_bytes()),
    'stderr_sha256': sha((HERE / '05-AUDIT.stderr').read_bytes()),
    'product_tests_rerun': False, 'HOME_CODEX_HOME_override': False,
    'original_five_commands': 'exact argv/cwd and original stream/receipt bindings in 03-FIVE-ORIGINAL-COMMAND-STREAM-RECEIPT-BINDINGS.json'
})
report = '''Independent evidence review found 0 new blocking issues on Standards and 0 on Spec, within this finite evidence scope. The original fixed-101 full Python command actually returned uv exit 0 and wrapper exit 0: 4587 passed, 2 skipped, 3 warnings in 3172.43s, collected 4589. Both skips are numeric BLOCKED_ENVIRONMENT, not numeric PASS. This review does not accept the whole M6.3 phase or unlock M7.

The fixed source is 101cee47d8e746dddac81fb6e8829069fcabff09, tree 58da1a9c891c9cd3d9f5595e7ea9edcb8c65c2ff. All 56 original files match their manifest SHA256, byte lengths and exact path set. The original manifest SHA256 is dfae73881cddf96d636f36458f0c6971e76b2089f9ce6b5df33f81c9a8cb4ba2. All 13 captured complete source maps retain the same 1564 paths and exact fixed Git records, index mode/type/blob/stage and live mode/type/blob/size/SHA256. These maps do not contain complete stat/inode/mtime evidence. Captured canonical evidence excludes progress/; it does not prove whole canonical index cleanliness. No current canonical or source checkout was reread, and later archival .gitattributes changes are outside this original temporal gate.

The five original stages (worktree creation, declared Node archive reuse, make setup, Node version, and full Python) retain original command/stream/receipt bindings and actual exit 0. The full command is uv run --frozen --offline pytest, retry 0, with no subset filter or replacement test config. Its original stdout is 27471 bytes, SHA256 960f512d4d282d43c46bf109291f80769dd846d026cb5899b391b64eaa72085a; stderr is empty. The wrapper elapsed time is 3174.0383118089994s, distinct from the pytest footer duration. Only the collection line, exact footer, and the two original numeric skip lines are selected after verifying the full stdout hash. No full stdout, AuthCase/CSRF/fixture body, raw API payload, actual DB, ZIP, screenshot, profile or private form is copied into this candidate.

The independent final FINAL.json SHA256 363a05abc90fbe512d7f5905d12dea29d5081dbf796e39b304604ed9c5e14b17 and manifest SHA256 79527851f6f1b0f729a7c82bca523565cca5c64c76ccf249a8d7d649ef3c96d4 match the originals and terminal counts. The original RESULT.json still says PENDING_FREEZE because it precedes the later final closure; it is preserved. The later FINAL binds captured source and canonical closures to 101 with all 1564 inputs exact. It is not a rewrite of that original phase record.

The original literal command environments did not reassign HOME or CODEX_HOME. They are not claimed byte-identical to previous runs. Public dependency installation used network; uv --offline for the test command is not a host zero-network proof. Host isolation, production provider/real Codex turn qualification and physical runtime safety were not tested by this audit. The two numeric environment skips remain unresolved. Original 079 failures, the scoped 8bd 6-pass record and the separate 133-pass native record remain independent and their counts are not added to this gate.

REVIEW.json and 01 through 04 record the independent checks. The audit's actual tool chunk b7cc0f exited 0; its stdout/stderr and script are retained. Exact shell text was not separately captured, so the receipt states that limitation instead of reconstructing it. This packaging checks explicit count/path consistency and copies only ten admitted original metadata files. No product tests, models, host probes, source edits, canonical writes or remote actions were run by this reviewer. PASS here means finite provenance and captured source consistency; ENV covers the two numeric skips; full stat and host zero-network proof are NOT_CAPTURED/NOT_PROVEN; whole M6.3 is NOT_ACCEPTED.
'''
put('REPORT.md', report.encode())
print(json.dumps({'copied_original_metadata_files': len(copies),
                  'originals_checked': 56, 'full_source_maps_checked': 13,
                  'Standards_new_blocking': 0, 'Spec_new_blocking': 0,
                  'product_tests_rerun': False}, sort_keys=True))
