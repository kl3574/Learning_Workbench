"""Read fixed Git objects and explicit existing evidence; create a private candidate seal."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess
os.umask(0o077)
e = Path(__file__).resolve().parent
r = e.parent / 'm63-codex-restore-lifespan-oct05'
s = e / 'seal-7cff'
s.mkdir(mode=0o700)
sha = lambda b: hashlib.sha256(b).hexdigest()
def save(name, data):
 p=s/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else (json.dumps(data,indent=2)+'\n').encode());return p
base='942fc533ca48e1a561199fb992d80e76622948c1'
head='7cffb5305321c53258f5c5601a4ca7c29b5b4801'
def git(*args): return subprocess.check_output(['git',*args],cwd=r)
assert git('rev-parse','HEAD').decode().strip()==head and git('status','--porcelain')==b''
heads=[base]+git('rev-list','--reverse',base+'..'+head).decode().splitlines()
rows={};oids=set()
for h in heads:
 entries=[]
 for line in git('ls-tree','-rz',h).split(b'\0'):
  if not line:continue
  a,p=line.split(b'\t');mode,kind,oid=a.decode().split();path=p.decode()
  if kind!='blob' or path.startswith('progress/'):continue
  entries.append(dict(path=path,mode=mode,type=kind,git_blob=oid));oids.add(oid)
 rows[h]=entries
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=r,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
raw,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blobs={}
for oid in sorted(oids):
 end=raw.index(b'\n',at);actual,kind,size=raw[at:end].decode().split();size=int(size);data=raw[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blobs[oid]=(size,sha(data))
assert at==len(raw)
for h,entries in rows.items():
 for item in entries:item.update(bytes=blobs[item['git_blob']][0],sha256=blobs[item['git_blob']][1])
 save('git/'+h+'.json',dict(head=h,count=len(entries),files=entries))
final={x['path']:x for x in rows[head]};old={x['path']:x for x in rows[base]}
changed=[p for p in final if p not in old or final[p]!=old[p]]
assert sorted(changed)==['tests/integration/test_backup_codex_lifespan.py']
assert len(final)==1524 and len(old)==1523
for p,item in final.items():
 data=os.readlink(r/p).encode() if item['mode']=='120000' else (r/p).read_bytes()
 assert len(data)==item['bytes'] and sha(data)==item['sha256']
stages=['focused-01','static-01','diff-01','focused-02','static-02','diff-02','related-01']
history=[];map_bindings=0
for name in stages:
 d=e/name;receipt=json.loads((d/'receipt.json').read_text());h=receipt['source_sha'];ref={x['path']:x for x in rows[h]}
 before=json.loads((d/'source-before.json').read_text());after=json.loads((d/'source-after.json').read_text())
 assert before==after and before['head']==h and before['status']=='' and before['count']==len(ref)
 for snap in [before,after]:
  assert len(snap['files'])==len(ref)
  for item in snap['files']:
   assert item['matches_git'] and item['actual_blob']==item['git_blob']
   assert all(item[k]==ref[item['path']][k] for k in ['mode','type','git_blob','bytes','sha256'])
   map_bindings+=1
 assert sha((d/'run.log').read_bytes())==receipt['log_sha256']
 for p,hv in receipt['test_sources'].items():assert sha((d/Path(p).name).read_bytes())==hv==ref[p]['sha256']
 if 'harness_inputs' in receipt:
  for p,hv in receipt['harness_inputs'].items():assert sha((e/p).read_bytes())==hv
 history.append(dict(stage=name,**receipt))
save('STAGE_HISTORY.json',history)
save('owned.patch',git('diff','--binary',base,head,'--',*changed))
for p in changed:save('source/'+p,(r/p).read_bytes())

summary=dict(base=base,head=head,sole_spec_sha256=sha((r/'PRODUCT_DESIGN.md').read_bytes()),changed_paths=changed,complete_base_inputs=len(old),complete_final_inputs=len(final),unchanged_base_inputs=sum(p in final and v==final[p] for p,v in old.items()),git_heads=heads,git_bindings=sum(map(len,rows.values())),distinct_git_blobs=len(blobs),stages=len(stages),before_after_map_bindings=map_bindings,live_all_final_exact=True,qualification='Original FAIL and later PASS have different test oracles; no production fix or same-test RED-GREEN claim',stage_sources_unchanged=True,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
save('SOURCE_BINDINGS.json',summary)
print(json.dumps(summary,indent=2))
