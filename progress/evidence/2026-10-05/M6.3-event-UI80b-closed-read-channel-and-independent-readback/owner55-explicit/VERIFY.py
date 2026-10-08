from pathlib import Path
import hashlib,json
root=Path(__file__).parent
sha=lambda data:hashlib.sha256(data).hexdigest()
for manifest in ['RAW_MANIFEST.json','OUTER_MANIFEST.json']:
 for entry in json.loads((root/manifest).read_text())['files']:
  raw=(root/entry['path']).read_bytes();assert sha(raw)==entry['sha256'] and len(raw)==entry['bytes'],entry['path']
entries=json.loads((root/'SAFE_SHARE.json').read_text())['files']
for entry in entries:
 raw=(root/entry['path']).read_bytes();candidate=(root/entry['candidate']['path']).read_bytes()
 assert sha(raw)==entry['raw']['sha256'] and len(raw)==entry['raw']['bytes'],entry['path']
 assert sha(candidate)==entry['candidate']['sha256'] and len(candidate)==entry['candidate']['bytes'],entry['path']
 assert candidate==(raw if entry['transform']=='binary-exact' else raw.replace(b'$HOME',b'<LOCAL_HOME>')),entry['path']
actual={str(p.relative_to(root/'SAFE_SHARE')) for p in (root/'SAFE_SHARE').rglob('*') if p.is_file()}
assert actual=={entry['path'] for entry in entries}
for stage in ['fixed-80b405a9','native-80b405a9','native-02-80b405a9','native-03-80b405a9','native-04-80b405a9','native-types-05']:
 before=json.loads((root/stage/'inputs-before.json').read_text());after=json.loads((root/stage/'inputs-after.json').read_text());receipt=json.loads((root/stage/'receipt.json').read_text())
 assert before==after and len(before)==1499 and all(v['git_exact'] and v['sha256']==v['git_sha256'] for v in before.values()),stage
 assert receipt['source_equal'] and receipt['all_git_exact'] and receipt['git_status']=='',stage
 assert receipt.get('private_unchanged',True),stage
 assert sha((root/stage/'run.py').read_bytes())==receipt['runner_sha256'],stage
 for entry in receipt['commands']:
  assert sha((root/stage/(entry['name']+'.log')).read_bytes())==entry['log_sha256'],stage
result={'status':'PASS','raw_count':len(json.loads((root/'RAW_MANIFEST.json').read_text())['files']),'candidate_count':len(entries),'fixed_engineering_count':1499,'fixed_maps_equal':True,'raw_and_candidate_hashes':True,'only_exact_declared_transform':True,'separate_failures_preserved':True}
print(json.dumps(result,indent=2))
