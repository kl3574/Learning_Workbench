"""Collection-only proof for two failed synthetic tmp_path cases; no fixtures execute."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
SOURCE=Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-full-python-source-dcfda8c2-oct03')
EVIDENCE=Path(__file__).parent
FIXED='dcfda8c270dff3e6db75011c50ffa7d6f5826512'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(name,value):(EVIDENCE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def snapshot():
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
    assert actual==FIXED,'fixed HEAD changed'
    unexpected=[p for p in subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=SOURCE).split(b'\0') if p and not p.startswith(b'progress/')]
    assert not unexpected,'untracked engineering inputs present'
    entries=[]
    for item in subprocess.check_output(['git','ls-tree','-r','-z',FIXED],cwd=SOURCE).split(b'\0'):
        if not item:continue
        meta,raw_name=item.split(b'\t',1);name=raw_name.decode();mode,kind,blob=meta.decode().split()
        if name.startswith('progress/'):continue
        assert kind=='blob',name
        entries.append((name,mode,blob))
    stream=subprocess.check_output(['git','cat-file','--batch'],cwd=SOURCE,input=''.join(blob+'\n' for _,_,blob in entries).encode())
    offset=0;files={}
    for name,mode,blob in entries:
        end=stream.index(b'\n',offset);header=stream[offset:end].decode().split();size=int(header[2]);start=end+1
        expected=stream[start:start+size];offset=start+size+1
        assert header[:2]==[blob,'blob'] and stream[offset-1:offset]==b'\n'
        raw=(SOURCE/name).read_bytes()
        assert raw==expected,'Git byte mismatch: '+name
        files[name]={'sha256':sha(raw),'bytes':len(raw),'git_blob':blob,'git_mode':mode,'exact_git_bytes':True}
    assert offset==len(stream)
    runner=Path(__file__).read_bytes()
    return {'head':actual,'scope':'Every tracked nonprogress engineering input, exact bytes from fixed Git; no untracked engineering probes. Progress, ignored installed dependencies/runtime/cache outputs excluded.',
            'count':len(files),'files':files,'private_inputs':{'collect_mapping.py':{'sha256':sha(runner),'bytes':len(runner)}}}
before=snapshot();write('inputs-before.json',before)
command=['uv','run','--frozen','--no-sync','pytest','--collect-only','-q',
 'tests/integration/test_draft_candidate_owners.py::test_missing_provider_owner_cannot_reuse_registered_candidate',
 'tests/integration/test_review_http.py::test_review_http_write_guards_and_strict_request',
 '-o','cache_dir='+str(EVIDENCE/'collection-cache')]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':''}
with (EVIDENCE/'collection.log').open('wb') as out:
 code=subprocess.call(command,cwd=SOURCE,env=env,stdout=out,stderr=subprocess.STDOUT)
assert code==0
nodes=[line for line in (EVIDENCE/'collection.log').read_text().splitlines() if line.startswith('tests/integration/') and '::' in line]
assert len(nodes)==14
counts={};mapping={}
for node in nodes:
 prefix=re.sub(r'[\W]','_',node.split('::')[-1])[:30]
 n=counts.get(prefix,0);counts[prefix]=n+1
 mapping[node]=prefix+str(n)
base=Path('$HOME/.cache/lw-m63-dcf-oct03/pytest')
for prefix,count in counts.items():
 actual=sorted(p.name for p in base.iterdir() if p.name.startswith(prefix) and not p.is_symlink())
 assert actual==sorted(prefix+str(n) for n in range(count))
assert not list(SOURCE.glob('**/conftest.py')) # isolated source has no installed node_modules
failed=json.loads(Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-full-python-dcfda8c2-oct03/pytest-cache/v/cache/lastfailed').read_text())
selected={node:directory for node,directory in mapping.items() if node in failed}
assert len(selected)==2
after=snapshot();write('inputs-after.json',after);assert after==before
write('mapping.json',{'fixed_head':FIXED,'command':command,'exit_code':code,'scope':'collection only; no fixture/test body or CLI/provider execution',
 'inputs_unchanged':True,'input_count':before['count'],'all_collected':mapping,'failed_selected':selected,
 'proof':['Original explicit basetemp belonged solely to completed fixed full invocation, without xdist or retry options.',
 'Installed pytest tmpdir._mk_tmp uses sanitized node.name truncated to 30; numbered directories start 0 and increment.',
 'All colliding cases belong to exactly these two source test functions; fixture/decorator order agrees with this collection-only readback.',
 'No source conftest override; observed directories exactly cover 2 and 12 cases respectively, with final current symlinks at 1 and 11.',
 'Original full log and original cache lastfailed identify single and extra_body-decision; database contents are not used for identity inference.']})
print(json.dumps({'collected':len(nodes),'failed_selected':selected,'exact_git_inputs':before['count']}))
