"""Complete fixed-source contract/unit/integration gate; no source mutation."""
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
SOURCE=Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-full-python-source-1843556e-oct04')
EVIDENCE=Path(__file__).parent
FIXED='1843556e1c01b48e60082969e78d2a82b3848b45'
TEMP=Path('$HOME/.cache/lw-m63-1843-oct04')
COMMAND=['uv','run','--frozen','--no-sync','pytest','tests/contract','tests/unit','tests/integration',
         '--tb=short','--basetemp='+str(TEMP/'pytest'),'-o','cache_dir='+str(EVIDENCE/'pytest-cache')]
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
            'count':len(files),'files':files,'private_inputs':{'run_full_python.py':{'sha256':sha(runner),'bytes':len(runner)}}}
before=snapshot();write('inputs-before.json',before)
start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
write('status.json',{'state':'RUNNING','head':FIXED,'command':COMMAND,'started_at':start,'input_count':before['count'],'runner_sha256':before['private_inputs']['run_full_python.py']['sha256']})
print('RUNNING complete Python gate; fixed '+FIXED+'; '+str(before['count'])+' exact Git inputs',flush=True)
env={**os.environ,'TMPDIR':str(TEMP),'PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':''}
with (EVIDENCE/'python.log').open('wb') as output:
    process=subprocess.Popen(COMMAND,cwd=SOURCE,env=env,stdout=output,stderr=subprocess.STDOUT)
    code=process.wait()
duration=time.monotonic()-tick
try:
    after=snapshot();write('inputs-after.json',after);unchanged=before==after;snapshot_error=None
except Exception as error:
    unchanged=False;snapshot_error=type(error).__name__+': '+str(error)
receipt={'state':'PASS' if code==0 and unchanged else 'FAIL','head':FIXED,'source_tree':str(SOURCE),'command':COMMAND,
 'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(duration,3),'exit_code':code,
 'input_count':before['count'],'inputs_unchanged':unchanged,'exact_git_bytes':unchanged,'source_snapshot_error':snapshot_error,
 'runner':before['private_inputs']['run_full_python.py'],'log_sha256':sha((EVIDENCE/'python.log').read_bytes()),
 'inputs_before_sha256':sha((EVIDENCE/'inputs-before.json').read_bytes()),
 'inputs_after_sha256':sha((EVIDENCE/'inputs-after.json').read_bytes()) if (EVIDENCE/'inputs-after.json').exists() else None,
 'environment_overrides':{'TMPDIR':'private short per-run directory','PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':''},
 'scope':'Complete tests/contract tests/unit tests/integration, no -k/-x/collection exclusion. Existing environment skips retained. Not Web/native/security-extension or model acceptance.'}
write('receipt.json',receipt);write('status.json',receipt)
print(json.dumps({k:receipt[k] for k in ('state','exit_code','duration_seconds','input_count','inputs_unchanged')}),flush=True)
sys.exit(code if unchanged else 99)
