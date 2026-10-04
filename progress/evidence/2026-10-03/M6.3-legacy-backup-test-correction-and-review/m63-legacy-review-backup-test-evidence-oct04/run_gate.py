"""Fixed-source ordinary pytest stages; immutable original full failure is separate."""
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
SOURCE=Path('$HOME/.cache/learning-workbench-acceptance/m63-legacy-review-backup-test-oct04')
ROOT=Path(__file__).parent
FIXED=sys.argv[1]
PHASE=sys.argv[2]
EVIDENCE=ROOT/PHASE
EVIDENCE.mkdir()
TEMP=Path('$HOME/.cache/lw-m63-backup-oct04')/PHASE
TEMP.mkdir()
COMMAND=['uv','run','--frozen','--no-sync',*sys.argv[3:]]
if sys.argv[3]=='pytest':
    COMMAND += ['--tb=short','--basetemp='+str(TEMP/'pytest'),'-o','cache_dir='+str(EVIDENCE/'pytest-cache')]
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
            'count':len(files),'files':files,'private_inputs':{'run_gate.py':{'sha256':sha(runner),'bytes':len(runner)}}}
before=snapshot();write('inputs-before.json',before)
start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
env={**os.environ,'TMPDIR':str(TEMP),'PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':''}
with (EVIDENCE/'output.log').open('wb') as output:
    code=subprocess.call(COMMAND,cwd=SOURCE,env=env,stdout=output,stderr=subprocess.STDOUT)
duration=time.monotonic()-tick
after=snapshot();write('inputs-after.json',after)
receipt={'head':FIXED,'phase':PHASE,'command':COMMAND,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),
 'duration_seconds':round(duration,3),'exit_code':code,'inputs_unchanged':before==after,'input_count':before['count'],
 'runner':before['private_inputs']['run_gate.py'],'log_sha256':sha((EVIDENCE/'output.log').read_bytes()),
 'scope':'Test-only narrow backup/migration validation, not complete Python acceptance; no real login/human review.'}
write('receipt.json',receipt)
print(json.dumps(receipt),flush=True)
sys.exit(code if before==after else 99)
