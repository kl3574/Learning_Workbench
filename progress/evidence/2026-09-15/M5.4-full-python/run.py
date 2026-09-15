"""Full Python test gate on an explicit commit; no product edits or shell expansion."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('[LOCAL_HOME]/.cache/learning-workbench-acceptance/m54-active')
OUT=Path(__file__).parent
COMMIT='64b5db92ec20af3b7c7a0e2175665ccbc3ebaded'
COMMAND=['.venv/bin/python','-B','-m','pytest']
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def snapshot():
 names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
 files=[]
 for name in sorted(set(x for x in names if x and not x.startswith('progress/'))):
  p=ROOT/name
  if p.is_symlink(): b=os.readlink(p).encode();kind='symlink'
  elif p.is_file(): b=p.read_bytes();kind='file'
  else:
   files.append({'path':name,'kind':'missing','bytes':None,'sha256':None});continue
  files.append({'path':name,'kind':kind,'bytes':len(b),'sha256':sha(b)})
 return {'scope':'All git cached + untracked nonignored paths except progress/**; includes generated/locks/toolchain configuration and tracked output PNGs',
         'count':len(files),'files':files,'aggregate_sha256':sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())}
def git_compare(actual):
 expected={}
 for row in subprocess.check_output(['git','ls-tree','-rz',COMMIT],cwd=ROOT).split(b'\0'):
  if not row:continue
  rawheader,rawname=row.split(b'\t',1);name=rawname.decode();mode,kind,oid=rawheader.decode().split()
  if not name.startswith('progress/'):
   assert kind=='blob',(name,kind)
   expected[name]=(mode,oid)
 values={x['path']:x for x in actual['files']}
 records=[]
 for name in sorted(expected.keys()|values.keys()):
  p=ROOT/name
  raw=os.readlink(p).encode() if p.is_symlink() else p.read_bytes() if p.is_file() else None
  oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() if raw is not None else None
  mode='120000' if p.is_symlink() else '100755' if p.is_file() and p.stat().st_mode & 0o111 else '100644'
  match=name in values and expected.get(name)==(mode,oid)
  records.append({'path':name,'git_blob':expected.get(name,[None,None])[1],
                  'actual_git_blob':oid,'git_mode':expected.get(name,[None,None])[0],'actual_mode':mode,'matches':match})
 return {'commit':COMMIT,'expected_count':len(expected),'actual_count':len(values),'all_match':all(x['matches'] for x in records),'files':records}
if len(sys.argv)>1:
 assert sys.argv[1]=='--preflight'
 current=snapshot();comparison=git_compare(current)
 assert head()==COMMIT and current['count']==comparison['expected_count'] and comparison['all_match']
 write(OUT/'preflight.json',{'recorded_at':now(),'commit':COMMIT,'command':COMMAND,'driver_sha256':sha(Path(__file__).read_bytes()),
                           'source_count':current['count'],'source_aggregate':current['aggregate_sha256'],'actual_run_started':False})
 print(f"Preflight: {current['count']} current non-progress inputs match fixed Git commit; test not started.")
 sys.exit(0)
assert not (OUT/'run.log').exists(), 'Immutable output already exists'
before=snapshot();comparison=git_compare(before)
write(OUT/'source-before.json',before);write(OUT/'git-source-before.json',comparison)
assert head()==COMMIT and before['count']==comparison['expected_count'] and comparison['all_match']
started=now()
write(OUT/'running.json',{'started_at':started,'command':COMMAND,'commit':COMMIT,'driver_sha256':sha(Path(__file__).read_bytes()),'source_before_sha256':sha((OUT/'source-before.json').read_bytes())})
env=dict(os.environ,TMPDIR='[LOCAL_HOME]/.cache/lw-proof54',PYTHONDONTWRITEBYTECODE='1')
with (OUT/'run.log').open('wb') as log:
 code=subprocess.run(COMMAND,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
finished=now();after=snapshot();aftercomparison=git_compare(after)
write(OUT/'source-after.json',after);write(OUT/'git-source-after.json',aftercomparison)
b={x['path']:x for x in before['files']};a={x['path']:x for x in after['files']}
changes=[p for p in sorted(b.keys()|a.keys()) if b.get(p)!=a.get(p)]
receipt={'command':COMMAND,'cwd':str(ROOT),'fixed_commit':COMMIT,'git_after':head(),'started_at':started,'finished_at':finished,'exit_code':code,
         'driver_sha256':sha(Path(__file__).read_bytes()),'log_sha256':sha((OUT/'run.log').read_bytes()),
         'source_before_count':before['count'],'source_after_count':after['count'],
         'source_before_aggregate':before['aggregate_sha256'],'source_after_aggregate':after['aggregate_sha256'],
         'all_source_matches_git_before':comparison['all_match'],'all_source_matches_git_after':aftercomparison['all_match'],
         'source_unchanged':not changes,'changed_inputs':changes,
         'artifacts':{name:sha((OUT/name).read_bytes()) for name in ('source-before.json','source-after.json','git-source-before.json','git-source-after.json','preflight.json')}}
write(OUT/'receipt.json',receipt)
print((OUT/'run.log').read_text()[-5000:])
print(json.dumps(receipt,indent=2))
sys.exit(code if code else 0 if not changes and aftercomparison['all_match'] else 1)
