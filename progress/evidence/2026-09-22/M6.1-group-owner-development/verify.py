"""Read-only integrity verification; never runs the archived commands."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":")).encode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-base',type=Path);parser.add_argument('--raw-home');args=parser.parse_args()
    assert (args.raw_base is None)==(args.raw_home is None)
    root=Path(__file__).resolve().parent;manifest=json.loads((root/'manifest.json').read_bytes())
    files=manifest['public_files'];assert sha(canonical(files))==manifest['public_aggregate_sha256']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual=={r['path'] for r in files}|{'manifest.json'}
    for r in files:
        p=root/r['path'];assert not p.is_symlink() and p.resolve().is_relative_to(root.resolve())
        data=p.read_bytes();assert len(data)==r['bytes'] and sha(data)==r['sha256']
    aliases={r['raw_relative']:r for r in manifest['aliases']};assert len(aliases)==len(manifest['aliases'])
    replayed=0
    for r in aliases.values():
        data=(root/r['public_path']).read_bytes();assert len(data)==r['public_bytes'] and sha(data)==r['public_sha256']
        if args.raw_base:
            path=args.raw_base/r['raw_relative'];assert path.resolve().is_relative_to(args.raw_base.resolve()) and not path.is_symlink()
            raw=path.read_bytes();assert len(raw)==r['raw_bytes'] and sha(raw)==r['raw_sha256']
            assert raw.count(args.raw_home.encode())==r['home_substitutions']
            assert raw.replace(args.raw_home.encode(),b'<LOCAL_HOME>')==data;replayed+=1
    checked=0
    for name,r in aliases.items():
        if not name.endswith('/receipt.json'):continue
        value=json.loads((root/r['public_path']).read_bytes());prefix=name.removesuffix('receipt.json')
        for sibling,expected in value['files'].items():
            alias=aliases[prefix+sibling];assert expected['sha256']==alias['raw_sha256'] and expected['bytes']==alias['raw_bytes']
        before,after=(json.loads((root/aliases[prefix+n]['public_path']).read_bytes()) for n in ['before.json','after.json'])
        assert len(before)==value['input_count_before'] and len(after)==value['input_count_after']
        assert (before==after)==value['declared_inputs_unchanged'];checked+=1
    assert checked==18
    print(json.dumps({'status':'PASS','public_files':len(actual),'raw_aliases':len(aliases),'raw_replays':replayed,'original_receipts':checked,'tests_rerun':False}))
if __name__=='__main__':main()
