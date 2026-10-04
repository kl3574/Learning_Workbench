"""Read-only inventory verification. Never writes or imports application modules."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source = json.loads((root / 'SOURCE_BINDINGS.json').read_bytes())
    for item in source['entries']:
        raw = (root / 'fixed-source' / item['path']).read_bytes()
        fixed = subprocess.check_output(['git', 'show', source['source_head'] + ':' + item['path']], cwd=args.repository)
        assert raw == fixed and digest(raw) == item['sha256'] and len(raw) == item['bytes']
    raw_manifest = json.loads((root / 'RAW_MANIFEST.json').read_bytes())
    for item in raw_manifest['files']:
        raw = (root / item['path']).read_bytes()
        assert digest(raw) == item['sha256'] and len(raw) == item['bytes']
    safe = json.loads((root / 'SAFE_SHARE.json').read_bytes())
    for item in safe['files']:
        raw = (root / item['path']).read_bytes()
        public = (root / 'safe-share' / item['path']).read_bytes()
        assert digest(raw) == item['raw_sha256'] and digest(public) == item['public_sha256']
        assert public == raw.replace(b'$HOME', b'$HOME')
    print(json.dumps({'status': 'PASS', 'fixed_source_files': len(source['entries']),
                      'raw_files': len(raw_manifest['files']), 'safe_files': len(safe['files']),
                      'source_head': source['source_head'], 'product_execution': False,
                      'db_reads': 0, 'network_calls': 0, 'files_written': 0}))


if __name__ == '__main__':
    main()
