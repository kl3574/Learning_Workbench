import datetime, hashlib, importlib.util, json, subprocess
from pathlib import Path
B=Path(__file__).parent.parent
O=Path(__file__).parent
R=B/'m62-public-safe-oct02'
A=B/'m63-interrupt-operation-coexist-evidence-oct04'
P=B/'m63-interrupt-operation-test-static-6127-oct04'
sha=lambda d:hashlib.sha256(d).hexdigest()
def j(p): return json.loads(p.read_bytes())
spec=importlib.util.spec_from_file_location('publication_check',R/'scripts/check_publication.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
allow=j(A/'publication-candidates/allowlist.json')
assert allow['count']==24 and len(allow['files'])==24
assert sha((A/'publication-candidates/allowlist.json').read_bytes())=='ea4d0e065d261444bc6315424d650df296ba26e07ba2ea7415c5d51d1ad99662'
candidates=[]
for item in allow['files']:
 raw=(A/item['source']).read_bytes(); cand=(A/'publication-candidates'/item['candidate']).read_bytes()
 assert sha(raw)==item['raw_sha256'] and sha(cand)==item['candidate_sha256']
 assert cand==raw.replace(b'$HOME',b'<LOCAL_HOME>')
 assert raw.count(b'$HOME')==item['home_prefix_replacements']
 assert not module.inspect('progress/evidence/M6.3-mixed/'+item['candidate'],cand)
 candidates.append({'path':item['candidate'],'sha256':sha(cand)})
def git_files(head):
 lines=subprocess.check_output(['git','ls-tree','-r','-z',head],cwd=R).split(b'\0')
 result={}
 for line in filter(None,lines):
  meta,path=line.split(b'\t',1); mode,kind,oid=meta.split()
  name=path.decode();
  if not name.startswith('progress/'):
   assert kind==b'blob';result[name]=oid.decode()
 return result
cache={}
def verify_map(p):
 value=j(p);head=value['head'];assert value['status']=='' and value['count']==1465
 files=value['files'];assert len(files)==1465 and len({x['path'] for x in files})==1465
 if head not in cache:
  tree=git_files(head); assert len(tree)==1465
  payload=('\n'.join(tree.values())+'\n').encode()
  data=subprocess.check_output(['git','cat-file','--batch'],cwd=R,input=payload)
  offset=0;infos={}
  for oid in tree.values():
   end=data.index(b'\n',offset); hdr=data[offset:end].split();assert hdr[0].decode()==oid and hdr[1]==b'blob'
   length=int(hdr[2]);content=data[end+1:end+1+length];assert len(content)==length
   infos[oid]=sha(content);offset=end+length+2
  assert offset==len(data); cache[head]=(tree,infos)
 tree,infos=cache[head]
 assert {x['path'] for x in files}==set(tree)
 for x in files:
  assert x['git_blob']==tree[x['path']]==x['actual_blob'] and x['matches_git']
  assert x['sha256']==infos[x['git_blob']]
 return {'path':str(p.relative_to(A)),'sha256':sha(p.read_bytes()),'head':head,'count':1465}
binding=j(A/'FINAL_BINDING.json');assert sha((A/'FINAL_BINDING.json').read_bytes())=='ccb39c77766ed93e5a961c123efcaf65a54da46946e94601d1792d4b087fa028'
maps=[]
for name,values in binding['runs'].items():
 receipt=j(A/name/'receipt.json');assert receipt==values['receipt'] and sha((A/name/'receipt.json').read_bytes())==values['receipt_sha256']
 assert sha((A/name/'run.log').read_bytes())==receipt['log_sha256']
 assert (A/name/'source-before.json').read_bytes()==(A/name/'source-after.json').read_bytes()
 maps += [verify_map(A/name/'source-before.json'), verify_map(A/name/'source-after.json')]
 assert receipt['exit_code']==(1 if name=='initial-five' else 0)
for manifest,count in [('SAFE_SHARE.json',3),('OUTER_METADATA.json',3)]:
 value=j(P/manifest);assert len(value['files'])==count
 for name,descriptor in value['files'].items():
  data=(P/name).read_bytes();assert sha(data)==descriptor['sha256'] and len(data)==descriptor['bytes']
  assert not module.inspect('progress/evidence/M6.3-mixed-peer/'+name,data)
root={'status':'ROOT_VERIFIED_24_EXPLICIT_CANDIDATES_ALL_RECORDED_1465_MAPS_AND_PEER_3_SAFE_3_OUTER',
 'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':binding['fixed_sha'],
 'initial_source':binding['runs']['initial-five']['receipt']['source_sha'],'candidate_count':24,'candidates':candidates,'maps':maps,
 'peer_review_sha256':sha((P/'REVIEW.md').read_bytes()),'root_test_read':'new239line current test read before normalmerge; final delta/currentJob oracle and original ACK/count preservation reviewed',
 'initial_fail':'1FAIL/4PASS incorrect full dynamicJob view oracle; originalrawlog private SHA retained',
 'final_scope':'5 new PASS and9 related PASS overlap; Ruff/diff0; no new test execution by rootreadback',
 'boundary':'No canonical/source/progress mutation; no new CLI/provider/model/network/system probes; all candidates explicitly bounded. Archival prefix transform is not runnable equivalence.'}
(O/'READBACK.json').write_text(json.dumps(root,indent=2)+'\n')
print(json.dumps({'status':root['status'],'candidates':24,'map_count':len(maps),'sha256':sha((O/'READBACK.json').read_bytes())}))
