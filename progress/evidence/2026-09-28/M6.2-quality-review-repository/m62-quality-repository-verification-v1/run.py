from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess, sys, os, time
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-quality-repository-active')
CACHE=Path(__file__).parent

def snapshot():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    files=[]
    for entry in subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).split(b'\0'):
        if not entry: continue
        metadata, path=entry.split(b'\t',1); mode, blob, index=metadata.decode().split(); name=path.decode()
        if name.startswith('progress/'): continue
        item=ROOT/name; data=os.readlink(item).encode() if item.is_symlink() else item.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        files.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':blob,'actual_git_blob_sha1':actual,'git_matches':actual==blob,'git_mode':mode})
    return {'head':head,'status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'files':files}

def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
stage=CACHE/sys.argv[1];stage.mkdir()
command=sys.argv[2:]
before=snapshot();dump(stage/'before.json',before)
assert before['status']=='' and all(row['git_matches'] for row in before['files'])
start=datetime.now(timezone.utc).isoformat();tick=time.monotonic();timedout=False
with (stage/'test.log').open('wb') as stream:
    try:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=1500,
            env={'PATH':os.environ['PATH'],'HOME':str(Path.home()),'LANG':'C.UTF-8','CI':'1','PYTHONDONTWRITEBYTECODE':'1'})
        code=result.returncode
    except subprocess.TimeoutExpired: timedout=True;code=None
end=datetime.now(timezone.utc).isoformat();after=snapshot();dump(stage/'after.json',after)
log=(stage/'test.log').read_bytes()
receipt={'command':command,'code_commit':before['head'],'started_at':start,'ended_at':end,'seconds':time.monotonic()-tick,
    'exit_code':code,'timeout':timedout,'source_count':len(before['files']),'source_unchanged':before==after,
    'all_source_matches_git_before':all(row['git_matches'] for row in before['files']),
    'all_source_matches_git_after':all(row['git_matches'] for row in after['files']),
    'log_bytes':len(log),'log_sha256':hashlib.sha256(log).hexdigest()}
dump(stage/'receipt.json',receipt)
print(json.dumps(receipt));print(log.decode(errors='replace')[-3500:])
sys.exit(0 if code==0 and before==after else 1)
