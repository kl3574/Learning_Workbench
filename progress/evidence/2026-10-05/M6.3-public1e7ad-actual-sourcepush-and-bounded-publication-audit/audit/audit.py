import datetime,hashlib,json,subprocess,sys
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');r=b/'m62-public-safe-oct02';o=Path(__file__).parent
base='6671dd5c924edbac8ca7f479c4f51d4afec14480';head='1e7ad7a8656c0dc8373d4181fa3002f385ed1847';source='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
sys.path.insert(0,str(r/'scripts'))
from check_publication import inspect
def g(*a):return subprocess.check_output(['git',*a],cwd=r)
def sha(x):return hashlib.sha256(x).hexdigest()
def tree(ref):
 d={}
 for row in g('ls-tree','-rz',ref).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);d[p.decode()]=h.decode().split()
 return d
def put(name,value):(o/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
assert g('rev-parse','HEAD').decode().strip()==head and not g('status','--porcelain')
prior=(b/'m63-final6671-source-publication-audit-oct05/READONLY_PUBLICATION_REVIEW.json').read_bytes();assert sha(prior)=='80d1515af9f918a121182cbebc55e7ccc9360816a3b1e6e04a597581db77cfc5'
old,new,owner=tree(base),tree(head),tree(source)
assert len(old)==21841 and len(new)==22290
assert {p:v for p,v in new.items() if not p.startswith('progress/')}=={p:v for p,v in owner.items() if not p.startswith('progress/')}
changed=[p for p in new if old.get(p)!=new[p]];unchanged=[p for p in old if old[p]==new[p]];assert len(changed)==457 and len(unchanged)==21833 and set(old)<=set(new)
current=[];findings=[];cache={}
for p in changed:
 mode,typ,blob=new[p];assert typ=='blob'
 raw=g('cat-file','blob',blob);cache[blob]=raw
 hits=inspect(p,raw);findings.extend({'path':p,'finding':x} for x in hits)
 current.append({'path':p,'mode':mode,'type':typ,'blob':blob,'size':len(raw),'sha256':sha(raw),'finding_count':len(hits)})
objects=g('rev-list','--objects','--no-object-names',base+'..'+head).decode().splitlines();outgoing=[];types={};payloads=0
for oid in objects:
 typ=g('cat-file','-t',oid).decode().strip();types[typ]=types.get(typ,0)+1
 raw=cache.get(oid)
 if raw is None:raw=g('cat-file',typ,oid);cache[oid]=raw
 if typ=='tree':
  paths=[x.decode() for x in g('ls-tree','-r','--name-only','-z',oid).split(b'\0') if x]
  hits=[x for p in paths for x in inspect('progress/audit/tree-metadata.txt',p.encode())]
 else:hits=inspect('progress/audit/outgoing-'+typ+'.txt',raw)
 findings.extend({'object':oid,'type':typ,'finding':x} for x in hits);payloads+=len(raw)
 outgoing.append({'object':oid,'type':typ,'size':len(raw),'sha256':sha(raw),'finding_count':len(hits)})
put('CURRENT_CHANGED_BINDINGS.json',current);put('OUTGOING_OBJECT_BINDINGS.json',outgoing);put('FINDINGS.json',findings)
assert not findings
spec=(r/'PRODUCT_DESIGN.md').read_bytes();assert sha(spec)=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec' and (Path('$HOME/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()==spec)
s=json.loads((r/'progress/state.json').read_text());t=next(x for x in s['tasks'] if x['id']=='M6.3')
assert t['status']=='in_progress' and t['publication_head']==base and t['candidate_implementation_commit']==source
assert t['current_local_checkpoint']['python']['old_complete_input_exact'] is False and t['current_local_checkpoint']['owner_publication_seal']['status'].startswith('ROOT_QUALIFIED')
assert all(x['status']=='todo' for x in s['tasks'] if x['id'].startswith('M7.'))
user=Path('$HOME/Desktop/learning/Learning_Workbench');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=user)
report={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':head,'outgoing_base':base,'current_paths':len(new),'unchanged_current_paths':len(unchanged),
 'continuity_qualification':'21833 oldpath mode/type/blob entries exact to fixed6671, whose bounded full audit80d1515a was independently qualified; old payloads not rescanned thisturn. No removed paths.',
 'current_changed_paths':len(changed),'outgoing_objects':len(objects),'object_types':types,'outgoing_payload_bytes_read':payloads,'findings':[],
 'engineering_inputs':1541,'source_inputs_all_exact27f':True,'new_documentary_paths':437,
 'root_source_and_original_finite_gates':'49530focused/334related historical-scoped plus27f68focused/186related/5static independently qualified; 98exactcandidates/7Gitmaps10760bindings/15stages46204bindings; no rootrerun; whole4441Python ACTUALLY_RUNNING notPASS',
 'explicit_new_evidence_scope':'Eight explicit packages433newfiles plusfour currentprogressdocs. New98catalog candidates/88CI candidates explicit independentqualification; rawprivate fullsource receipt/logZIP excluded. OriginalFAIL/UNKNOWN/LOSS and separate corrections retained. HOME/runnerprefix transform only documented.',
 'state_integrity':'M6.3in_progress/M7todo;public6671; newwholePython ACTUALLY_RUNNING4441/nativewholeNOT_RUN; proof/profile/checker/runtime missing; no wholephase acceptance',
 'sole_spec_sha256':sha(spec),'user_checkout_clean_unchanged':True,'bounded_publication_pass':True,
 'manual_provenance_limits':'Specific eight package/readback scopes and actualowned Git source. No generalPII/comprehensiveacademic/physicalsecurity certification; no deniedhostprobes.',
 'source_push_or_remote_mutation':False,'actual_external_model_calls':0,'wholeM6_3_AC21_M7':'NOT_ACCEPTED'}
put('READONLY_PUBLICATION_REVIEW.json',report)
print(json.dumps({'fixed':head,'current':len(new),'unchanged':len(unchanged),'changed':len(changed),'outgoing':len(objects),'types':types,'findings':0}))
