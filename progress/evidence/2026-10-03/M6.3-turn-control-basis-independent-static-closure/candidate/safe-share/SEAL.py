from pathlib import Path
import json,hashlib,runpy
E=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();scan=runpy.run_path(str(E/'check_publication.py'))['inspect']
raw=[]
for name in ['REVIEW.md','SOURCE_BINDINGS.json','VERIFY.py','SEAL.py','check_publication.py','fixed-delta.patch']:
 b=(E/name).read_bytes();raw.append(dict(path=name,bytes=len(b),sha256=sha(b)))
(E/'RAW_MANIFEST.json').write_text(json.dumps(dict(count=len(raw),files=raw),indent=2)+'\n')
(E/'safe-share').mkdir(exist_ok=False);files=[]
for name in [x['path'] for x in raw if x['path']!='fixed-delta.patch']:
 b=(E/name).read_bytes();d=b.replace(b'$HOME',b'$HOME');assert not scan('progress/evidence/2026-10-04/M6.3-turn-control-closure/'+name,d)
 (E/'safe-share'/name).write_bytes(d);files.append(dict(path=name,raw_sha256=sha(b),raw_bytes=len(b),public_sha256=sha(d),public_bytes=len(d),home_prefix_replacements=b.count(b'$HOME')))
(E/'SAFE_SHARE.json').write_text(json.dumps(dict(count=len(files),transform='Exact operator-home prefix substitution only',files=files),indent=2)+'\n')
(E/'SCAN.json').write_text(json.dumps(dict(status='PASS',files=len(files),findings=[],scanner_sha256=sha((E/'check_publication.py').read_bytes())),indent=2)+'\n')
outer=[]
for name in ['RAW_MANIFEST.json','SAFE_SHARE.json','SCAN.json']:
 b=(E/name).read_bytes();assert not scan('progress/evidence/2026-10-04/M6.3-turn-control-closure/'+name,b);outer.append(dict(path=name,sha256=sha(b),bytes=len(b),transform='none'))
(E/'PUBLIC_OUTER_ALLOWLIST.json').write_text(json.dumps(dict(count=len(outer),files=outer),indent=2)+'\n')
print(json.dumps(dict(raw=len(raw),safe=len(files),outer=len(outer),scan='PASS')))
