import datetime
import hashlib
import json
import sys
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
root = base / 'm62-public-safe-oct02'
sys.path.insert(0, str(root / 'scripts'))
from check_publication import inspect
from progress import read_state, save

def sha(data):
    return hashlib.sha256(data).hexdigest()

def package(name, groups, summary):
    dest = root / 'progress/evidence/2026-10-07' / name
    assert not dest.exists()
    prepared = []
    for prefix, dirname, names in groups:
        for name_ in names:
            raw = (base / dirname / name_).read_bytes()
            safe = raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
            target = prefix + '/' + name_
            findings = inspect('progress/' + target, safe)
            assert not findings, (target, findings)
            prepared.append((target, raw, safe, dirname, name_))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir()
    entries = []
    for target, raw, safe, dirname, name_ in prepared:
        path = dest / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(safe)
        entries.append({'file': target, 'source_package': dirname, 'source_relative': name_, 'raw_sha256': sha(raw),
                        'published_sha256': sha(safe), 'transformation': 'exact personal-home/runner prefix replacement only' if raw != safe else 'none'})
    summary['recorded_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary['files'] = len(entries)
    (dest / 'REPORT.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    entries.append({'file': 'REPORT.json', 'published_sha256': sha((dest / 'REPORT.json').read_bytes()), 'transformation': 'new scoped summary'})
    (dest / 'manifest.json').write_text(json.dumps({'entries': entries}, indent=2) + '\n')
    for p in dest.rglob('*'):
        if p.is_file():
            assert not inspect(str(p.relative_to(root)), p.read_bytes()), str(p.relative_to(dest))
    print(name, len(entries) + 1)
    return str((dest / 'REPORT.json').relative_to(root))
