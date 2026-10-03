import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

BASE = Path('$HOME/.cache/learning-workbench-acceptance')
ROOT = BASE / 'm62-public-safe-oct02'
sha = lambda data: hashlib.sha256(data).hexdigest()
groups = []
counts = {}
for name in ('m63-bootstrap-owner-delta-852-oct03', 'm63-bootstrap-native-preparation-oct03'):
    directory = BASE / name
    raw = json.loads((directory / 'RAW_MANIFEST.json').read_text())
    safe = json.loads((directory / 'SAFE_SHARE.json').read_text())
    assert raw['count'] == safe['count'] == len(raw['files']) == len(safe['files'])
    by_name = {item['path']: item for item in safe['files']}
    assert len(by_name) == raw['count']
    for item in raw['files']:
        name_ = item['path']
        assert not Path(name_).is_absolute() and '..' not in Path(name_).parts
        original = (directory / name_).read_bytes()
        assert len(original) == item['bytes'] and sha(original) == item['sha256']
        record = by_name[name_]
        assert record['raw_sha256'] == item['sha256'] and record['raw_bytes'] == item['bytes']
        public = (directory / 'public-candidates' / name_).read_bytes()
        assert public == original.replace(b'$HOME', b'$HOME')
        assert sha(public) == record['public_sha256'] and len(public) == record['public_bytes']
    counts[name] = raw['count']
    groups.append((name, name, [i['path'] for i in raw['files']] + ['RAW_MANIFEST.json', 'SAFE_SHARE.json', 'SAFE_SCAN.json']))

bindings = [
    ('m63-bootstrap-owner-delta-852-oct03', 'service.py', '85293a6ddc074238f4508f50e7e19f7d523ee549', 'services/api/app/application/codex_bootstrap.py'),
    ('m63-bootstrap-owner-delta-852-oct03', 'http-tests.py', '85293a6ddc074238f4508f50e7e19f7d523ee549', 'tests/integration/test_codex_bootstrap_http.py'),
    ('m63-bootstrap-native-preparation-oct03', 'codex-bootstrap.spec.ts', '8c27de618d0b09f09f403f1471676b21329432a7', 'tests/e2e/codex-bootstrap.spec.ts'),
]
for name, file, head, path in bindings:
    original = (BASE / name / file).read_bytes()
    assert original == subprocess.check_output(['git', 'show', head + ':' + path], cwd=ROOT)
report = {
    'status': 'PASS_STATIC_EVIDENCE_READBACK_ONLY', 'original_files': counts, 'git_source_bindings': bindings,
    'boundary': 'Independent hash/byte/source readback. Owner P2 code closure is static852; terminal file count regression added31 and actually included264 focused final backend gate. Runtime is outside that narrow static review. Native preparation strict check is not native execution; new native a2d9 first execution separately FAIL before preparation/real thread.'
}
Path(__file__).with_name('READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
module_path = BASE / 'm62-v313-pushed-progress-sync-oct03/package.py'
spec = importlib.util.spec_from_file_location('existing_package_helper', module_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
groups.append(('independent', 'm63-bootstrap-static-root-delta-readback-oct03', ['verify_package.py', 'READBACK.json']))
public_report = helper.package('M6.3-bootstrap-static-owner-closure-and-native-preparation', groups, report.copy())
Path(__file__).with_name('PACKAGE_RECEIPT.json').write_text(json.dumps({'report': public_report}, indent=2) + '\n')
