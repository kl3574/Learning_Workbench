from pathlib import Path
import datetime,hashlib,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
BASE='1e7ad7a8656c0dc8373d4181fa3002f385ed1847';HEAD='079a008cf88b37e4517cb391503a1e7393ccf374';SOURCE='d78c4d159a2831f7d5e1721a9a466ec5b3e66421'
sys.path.insert(0,str(R/'scripts'));from check_publication import inspect
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def tree(ref):
 d={}
 for row in git('ls-tree','-rz',ref).split(b'\0'):
  if row:
   h,p=row.split(b'\t',1);d[p.decode()]=tuple(h.decode().split())
 return d
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
assert subprocess.run(['git','merge-base','--is-ancestor',BASE,HEAD],cwd=R).returncode==0
prior=(B/'m63-final1e7ad-bounded-publication-audit-oct05/READONLY_PUBLICATION_REVIEW.json').read_bytes();pr=json.loads(prior)
assert pr['source']==BASE and pr['current_paths']==22290 and pr['bounded_publication_pass'] and not pr['findings']
old,new,source=tree(BASE),tree(HEAD),tree(SOURCE)
assert len(old)==22290 and set(old)<=set(new)
engineering={p:v for p,v in new.items() if not p.startswith('progress/')};assert len(engineering)==1561
assert all(v==source[p] for p,v in engineering.items() if p!='.gitattributes')
changed=[p for p in new if old.get(p)!=new[p]];unchanged=[p for p in old if old[p]==new[p]]
cache={};findings=[];bindings=[]
for p in changed:
 mode,kind,blob=new[p];assert kind=='blob'
 raw=git('cat-file','blob',blob);cache[blob]=raw;hits=inspect(p,raw)
 findings.extend({'path':p,'finding':x} for x in hits)
 bindings.append({'path':p,'mode':mode,'type':kind,'git_blob':blob,'size':len(raw),'sha256':sha(raw),'findings':hits})
oids=git('rev-list','--objects','--no-object-names',BASE+'..'+HEAD).decode().splitlines();objects=[];types={};payloadbytes=0
for oid in oids:
 kind=git('cat-file','-t',oid).decode().strip();types[kind]=types.get(kind,0)+1
 raw=cache.get(oid)
 if raw is None:raw=git('cat-file',kind,oid);cache[oid]=raw
 if kind=='tree':
  paths=[p.decode() for p in git('ls-tree','-r','--name-only','-z',oid).split(b'\0') if p]
  hits=[h for p in paths for h in inspect('progress/audit/tree-metadata.txt',p.encode())]
 else:hits=inspect('progress/audit/outgoing-'+kind+'.txt',raw)
 findings.extend({'object':oid,'type':kind,'finding':h} for h in hits);payloadbytes+=len(raw)
 objects.append({'object':oid,'type':kind,'size':len(raw),'sha256':sha(raw),'findings':hits})
put('CURRENT_CHANGED_BINDINGS.json',bindings);put('OUTGOING_OBJECT_BINDINGS.json',objects);put('FINDINGS.json',findings)
assert not findings
spec=(R/'PRODUCT_DESIGN.md').read_bytes();assert sha(spec)=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
assert spec==Path('$HOME/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()
s=json.loads((R/'progress/state.json').read_bytes());t=next(x for x in s['tasks'] if x['id']=='M6.3')
assert t['status']=='in_progress' and t['candidate_implementation_commit']==SOURCE
assert all(x['status']=='todo' for x in s['tasks'] if x['id'].startswith('M7.'))
assert t['current_local_checkpoint']['python']['current1561']=='NOT_RUN' and t['current_local_checkpoint']['whole_M6_3_AC21_M7']=='NOT_ACCEPTED'
user=Path('$HOME/Desktop/learning/Learning_Workbench')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=user)
report={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':HEAD,'runtime_source_anchor':SOURCE,'outgoing_base':BASE,
 'current_paths':len(new),'unchanged_current_paths':len(unchanged),'changed_current_paths':len(changed),'outgoing_objects':len(oids),'object_types':types,'outgoing_payload_bytes_read':payloadbytes,
 'prior_public_audit_sha256':sha(prior),'continuity':'Old unchanged fixedpublic1e mode/type/blob exact; prior22290 bounded audit reused, oldpayload notrescanned; no removals',
 'engineering_inputs':1561,'runtime_source_exact_d78_except_attributes':True,'attributes':'Only three exact immutable archive whitespace rules; no original archived bytes changed',
 'current_runtime_qualification':'Broker6f22focused473related5static and Authoring3dstrict/build/5browser only; entirecurrent1561Python/native/CI NOT_RUN',
 'older_full_python':'Fixed68a4559PASS2realnumericENVskip3warnings; cannot cover newsource','old_public1eCI':'BothoriginaleventsFAIL/131PASS2FAIL each; localoldsourcegrading3PASS/Review1PASS notcauseclosure',
 'provenance_scope':'Nine explicit finite packages/453newfiles+earlier73ad412 archivefiles; full privateAPI/joblogs/DB/ZIP/PNG/profile/payload excluded. Root separate code/originalbyte qualification retained.',
 'findings':[],'bounded_publication_pass':True,'sole_spec_sha256':sha(spec),'user_b895_clean_unchanged':True,
 'sourcepush_merge_release_deploy':False,'model_calls':0,'production_proof_runtime':'UNIMPLEMENTED_UNQUALIFIED_DEFAULT_CLOSED','whole_M63_AC21_M7':'NOT_ACCEPTED',
 'limits':'Pattern scanner + finite provenance checks; no generalPII/academic/physical/runtime assurances. Source publicbranch push is not merge/release/deployment.'}
put('READONLY_PUBLICATION_REVIEW.json',report)
print(json.dumps({'source':HEAD,'current':len(new),'changed':len(changed),'unchanged':len(unchanged),'outgoing':len(oids),'types':types,'findings':len(findings)}))
