from pathlib import Path
import hashlib,json
P=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=json.loads((P/'RAW_MANIFEST.json').read_bytes())['files']
safe=json.loads((P/'SAFE_SHARE.json').read_bytes())['entries']
for x in raw:
 b=(P/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes'],x['path']
for x in safe:
 b=(P/x['source']).read_bytes();c=(P/x['candidate']).read_bytes()
 assert sha(b)==x['source_sha256'] and len(b)==x['source_bytes']
 assert c==b.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')
 assert sha(c)==x['sha256'] and len(c)==x['bytes']
print(json.dumps({'raw':len(raw),'safe':len(safe),'sha_bytes_exact_transforms':'PASS'}))
