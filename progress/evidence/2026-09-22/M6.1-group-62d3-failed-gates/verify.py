"""Verify eight historical gates and raw aliases without executing archived code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",", ":")).encode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-base',type=Path);parser.add_argument('--raw-home');parser.add_argument('--repo',type=Path);args=parser.parse_args()
    assert (args.raw_base is None)==(args.raw_home is None)
    root=Path(__file__).resolve().parent;manifest=json.loads((root/'manifest.json').read_bytes())
    files=manifest['public_files'];assert sha(canonical(files))==manifest['public_aggregate_sha256']
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}=={r['path'] for r in files}|{'manifest.json'}
    for row in files:
        path=root/row['path'];assert not path.is_symlink() and path.resolve().is_relative_to(root)
        data=path.read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    aliases={r['alias']:r for r in manifest['aliases']};assert len(aliases)==len(manifest['aliases'])
    replayed=0
    for row in aliases.values():
        public=(root/row['public_path']).read_bytes();assert sha(public)==row['public_sha256'] and len(public)==row['public_bytes']
        if args.raw_base:
            path=args.raw_base/row['raw_relative'];assert not path.is_symlink() and path.resolve().is_relative_to(args.raw_base.resolve())
            raw=path.read_bytes();assert len(raw)==row['raw_bytes'] and sha(raw)==row['raw_sha256']
            assert raw.count(args.raw_home.encode())==row['home_substitutions']
            assert raw.replace(args.raw_home.encode(),b'<LOCAL_HOME>')==public;replayed+=1
    def read(alias):return json.loads((root/aliases[alias]['public_path']).read_bytes())
    source=None;git=None
    for name in manifest['gate_names']:
        receipt=read(name+'/receipt.json');assert receipt['fixed_commit']==manifest['commit']==receipt['git_after']
        for field,sibling in [('log_sha256','run.log'),('source_before_sha256','source-before.json'),('source_after_sha256','source-after.json'),('git_before_sha256','git-before.json'),('git_after_sha256','git-after.json')]:
            assert receipt[field]==aliases[name+'/'+sibling]['raw_sha256']
        for file,pin in receipt['driver_hashes'].items():assert aliases[file]['raw_sha256']==pin
        before,after=read(name+'/source-before.json'),read(name+'/source-after.json');assert before==after
        assert before['count']==len(before['files'])==938
        assert sha(canonical(before['files']))==before['aggregate_sha256']==receipt['before_aggregate']==receipt['after_aggregate']
        beforegit,aftergit=read(name+'/git-before.json'),read(name+'/git-after.json');assert beforegit==aftergit
        assert beforegit['all_match'] and all(r['matches'] for r in beforegit['files'])
        assert receipt['unchanged'] and receipt['changed_inputs']==[] and receipt['git_match_before'] and receipt['git_match_after']
        if source is not None:assert source==before and git==beforegit
        source,git=before,beforegit
        assert receipt['exit_code']==(1 if name=='03-python' else 0)
    comparisons=0
    if args.repo:
        tree={}
        for line in subprocess.check_output(['git','ls-tree','-rz',manifest['commit']],cwd=args.repo).split(b'\0'):
            if not line:continue
            header,name=line.split(b'\t',1);mode,kind,oid=header.decode().split();name=name.decode()
            if not name.startswith('progress/'):assert kind=='blob';tree[name]=(mode,oid)
        assert len(tree)==938
        sources={r['path']:r for r in source['files']};assert set(tree)==set(sources)
        for row in git['files']:
            assert tree[row['path']]==(row['git_mode'],row['git_blob'])==(row['actual_mode'],row['actual_git_blob'])
            data=subprocess.check_output(['git','cat-file','blob',row['git_blob']],cwd=args.repo)
            assert sha(data)==sources[row['path']]['sha256'] and len(data)==sources[row['path']]['bytes'];comparisons+=1
    print(json.dumps({'status':'PASS','gates':len(manifest['gate_names']),'public_files':len(files)+1,'raw_replays':replayed,'git_comparisons':comparisons,'native':'NOT_RUN','historical_python':'2161 PASS, 1 FAIL, 1 ENV_SKIP; failure preserved','tests_executed':False}))
if __name__=='__main__':main()
