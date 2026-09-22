"""Verify public payloads; optionally replay explicit private raw bindings."""
import argparse
import hashlib
import json
from pathlib import Path

def transform(data, home, ci_home):
    return data.replace((home.rstrip('/')+'/').encode(), b'<USER_HOME>/').replace(home.rstrip('/').encode(), b'<USER_HOME>').replace((ci_home.rstrip('/')+'/').encode(), b'<CI_HOME>/').replace(b'/tmp/pytest-of-'+Path(home).name.encode(), b'<PYTEST_ROOT>')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home')
    parser.add_argument('--ci-home')
    args=parser.parse_args()
    if args.raw_base and (not args.raw_home or not args.ci_home): parser.error('--raw-home and --ci-home are required for raw replay')
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'manifest.json').read_bytes())
    for item in manifest['files']:
        actual=(root/item['public_path']).read_bytes()
        assert len(actual)==item['public_bytes'] and hashlib.sha256(actual).hexdigest()==item['public_sha256']
        if args.raw_base:
            raw=(args.raw_base/item['raw_cache']/item['raw_path']).read_bytes()
            assert len(raw)==item['raw_bytes'] and hashlib.sha256(raw).hexdigest()==item['raw_sha256']
            assert transform(raw,args.raw_home,args.ci_home)==actual
    print(f"PASS: {len(manifest['files'])} public payloads"+(' and raw transformations' if args.raw_base else ''))

if __name__=='__main__': main()
