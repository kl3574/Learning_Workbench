"""Verify every available HTTP evidence byte; report explicit uncaptured source/driver limits."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,subprocess

def sha(b):return hashlib.sha256(b).hexdigest()
def pin(b):return {'bytes':len(b),'sha256':sha(b)}
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def safe(base,name):
 p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
 return base/name
def checked(p,row,prefix=''):
 raw=p.read_bytes();assert pin(raw)=={'bytes':row[prefix+'bytes'],'sha256':row[prefix+'sha256']},str(p);return raw
def replay(raw,spans):
 chunks=[];end=0
 for s in spans:
  assert end<=s['start']<=s['end']<=len(raw);assert sha(raw[s['start']:s['end']])==s['raw_span_sha256']
  chunks.extend([raw[end:s['start']],s['replacement'].encode()]);end=s['end']
 return b''.join([*chunks,raw[end:]])
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--git-repo',type=Path);a.add_argument('--raw-base',type=Path);args=a.parse_args()
 root=Path(__file__).resolve().parent;m=json.loads((root/'manifest.json').read_bytes());expected={'manifest.json'}
 for r in m['public_files']:expected.add(r['path']);checked(safe(root,r['path']),r)
 assert expected=={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
 sm=json.loads((root/'source-map.json').read_bytes());sources={};missing={};git_count=0
 for digest,r in sm['sources'].items():
  if r['method']=='unavailable':missing[digest]=r;continue
  if r['method']=='public-git':
   if not args.git_repo:continue
   raw=subprocess.check_output(['git','show',sm['public_base']+':'+r['path']],cwd=args.git_repo);assert blob(raw)==r['git_blob'];git_count+=1
  else:assert r['method']=='file';raw=checked(safe(root,r['path']),r)
  assert pin(raw)=={'bytes':r['bytes'],'sha256':digest};sources[digest]=raw
 if args.raw_base:
  service_root=args.raw_base/'m62-general-draft-service-public-v1/public'
  assert sha((service_root/'manifest.json').read_bytes())==sm['service_package_manifest_sha256']
  for digest,row in sm['sources'].items():
   for origin in row.get('origins',[]):
    if origin['method']=='sealed-service-CAS':
     assert origin['manifest_sha256']==sm['service_package_manifest_sha256']
     assert safe(service_root,origin['path']).read_bytes()==sources[digest]
    elif origin['method']=='owner-backup':
     assert safe(args.raw_base/'m62-general-draft-http-development-v1',origin['path']).read_bytes()==sources[digest]
 commits={};actual_commits=[]
 for head,d in sm['commit_overrides'].items():
  c={p:r for p,r in sm['public_base_inputs'].items() if p not in d['absent']};c.update(d['overrides']);commits[head]=c
  if args.git_repo:
   tree=subprocess.check_output(['git','ls-tree','-rz',head],cwd=args.git_repo);seen=set()
   for item in tree.split(b'\0'):
    if not item:continue
    meta,name=item.split(b'\t');name=name.decode()
    if name.startswith('progress/'):continue
    mode,typ,git_blob=meta.decode().split();r=c[name];assert r['git_mode']==mode and r['git_blob']==git_blob
    assert pin(sources[r['sha256']])=={'bytes':r['bytes'],'sha256':r['sha256']};assert blob(sources[r['sha256']])==git_blob;seen.add(name)
   assert seen==set(c);actual_commits.append(head)
 im=json.loads((root/'input-map.json').read_bytes());base={r['path']:r for r in im['baseline']['files']};inputs={}
 for digest,d in im['snapshots'].items():
  rows={p:r for p,r in base.items() if p not in d['absent']};rows.update(d['overrides']);v={'head':d['head'],'files':[rows[p] for p in sorted(rows)]}
  raw=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();assert sha(raw)==digest;inputs[digest]=raw
  for r in rows.values():
   assert sm['sources'][r['sha256']]['bytes']==r['bytes'];assert r['git_matches']==(r['actual_blob']==r['indexed_blob'])
   if r['sha256'] in sources:assert blob(sources[r['sha256']])==r['actual_blob']
   elif r['sha256'] in missing:assert r['actual_blob']==missing[r['sha256']]['expected_actual_blob']
 mapped={};mapping_by_name={};covered={}
 for r in m['raw_mappings']:
  key=(r['raw_cache'],r['raw_path']);assert key not in mapped;covered.setdefault(key[0],set()).add(key[1])
  if r['method']=='file':raw=checked(safe(root,r['public_path']),r,'public_')
  elif r['method']=='input':raw=inputs[r['raw_sha256']]
  else:assert r['method']=='source';raw=sources.get(r['raw_sha256'])
  mapped[key]=raw;mapping_by_name[key]=r
  if args.raw_base:
   original=checked(safe(args.raw_base,key[0]+'/'+key[1]),r,'raw_');assert raw is not None,'Full replay requires --git-repo';assert replay(original,r.get('spans',[]))==raw
 inventory=json.loads((root/m['owner_inventory']).read_bytes());owner=inventory['cache'];assert covered[owner]==set(inventory['members'])
 for name,r in inventory['members'].items():assert mapping_by_name[(owner,name)]['raw_sha256']==r['sha256'] and mapping_by_name[(owner,name)]['raw_bytes']==r['bytes']
 if args.raw_base:
  actual={p.relative_to(args.raw_base/owner).as_posix():pin(p.read_bytes()) for p in sorted((args.raw_base/owner).rglob('*')) if p.is_file()};assert actual==inventory['members']
  for cache,r in m['raw_manifests'].items():
   raw=checked(safe(args.raw_base,cache+'/'+r['path']),r);members=json.loads(raw)['members'];names=set(members) if isinstance(members,dict) else {v['path'] for v in members};assert covered[cache]==names|{r['path']}
 recipes=json.loads((root/'source-reconstructions.json').read_bytes())
 for r in recipes:
  if r['basis_sha256'] not in sources:continue
  raw=sources[r['basis_sha256']];chunks=[];end=0
  for e in r['edits']:
   assert end<=e['start']<=e['end']<=len(raw);assert sha(raw[e['start']:e['end']])==e['original_span_sha256'];chunks.extend([raw[end:e['start']],e['replacement'].encode()]);end=e['end']
  result=b''.join([*chunks,raw[end:]]);assert result==sources[r['result_sha256']];assert len(result)==r['result_bytes'] and blob(result)==r['result_git_blob']
 stages=json.loads((root/'stage-bindings.json').read_bytes());complete=[];partial=[];drivers=[]
 for s in stages:
  name=s['stage'];r=json.loads(mapped[(owner,name+'/receipt.json')]);assert mapping_by_name[(owner,name+'/receipt.json')]['raw_sha256']==s['receipt_sha256'];assert r['exit_code']==s['exit_code']
  if name=='01-focused-initial':assert not any((owner,name+'/'+f) in mapped for f in ['test.log','inputs-before.json','inputs-after.json']);continue
  before=mapped[(owner,name+'/inputs-before.json')];after=mapped[(owner,name+'/inputs-after.json')];assert before==after and r['inputs_unchanged'];v=json.loads(before);assert sha(before)==s['input_sha256'];assert r['head']==v['head']==s['actual_head'];assert len(v['files'])==r['input_count']==s['input_count']
  log=mapping_by_name[(owner,name+'/test.log')];assert log['raw_sha256']==r['log_sha256']==s['log_sha256'] and log['raw_bytes']==r['log_bytes'];assert r['runner_sha256']==s['runner_sha256']
  if s['runner_original_path']:assert mapping_by_name[(owner,s['runner_original_path'])]['raw_sha256']==r['runner_sha256']
  else:drivers.append(name)
  unavailable=[row['path'] for row in v['files'] if row['sha256'] in missing];assert unavailable==s['unavailable_source_paths'];(partial if unavailable else complete).append(name)
  vals={row['path']:{'bytes':row['bytes'],'sha256':row['sha256']} for row in v['files']};assert s['matching_committed_bytes']==[head for head,c in commits.items() if vals=={p:{'bytes':row['bytes'],'sha256':row['sha256']} for p,row in c.items()}]
 print(json.dumps({'public_files':len(expected),'raw_mappings':len(mapped),'owner_files_covered':len(inventory['members']),'existing_raw_coverage':'COMPLETE','all_existing_raw_private_replay':bool(args.raw_base),'public_git_sources_verified':git_count,'actual_git_commits_verified':actual_commits,'input_snapshots_reconstructed':len(inputs),'input_paths':len(im['all_original_paths']),'stages':len(stages),'fully_reconstructed_source_stages':complete,'partially_reconstructed_source_stages':partial,'uncaptured_initial_stage':'01-focused-initial','unavailable_source_digests':list(missing),'stages_without_original_runner_bytes':drivers,'full_historical_source_and_driver_replay':'PARTIAL','excluded_existing_members':0,'excluded_log_lines':0,'product_tests':0,'network_requests':0},indent=2))
if __name__=='__main__':main()
