"""Offline explicit raw/candidate/outer checksum readback, with no app imports."""
from pathlib import Path
import hashlib,json,sys
base=Path(sys.argv[1])
def info(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
raw=json.loads((base/'RAW_MANIFEST.json').read_text())['files']
for path,value in raw.items():assert info((base/path).read_bytes())==value,path
safe=json.loads((base/'SAFE_SHARE.json').read_text())['files']
prefix=bytes([47,104,111,109,101,47,108,107,120])
for item in safe:
 original=(base/item['raw_path']).read_bytes(); candidate=(base/item['candidate_path']).read_bytes()
 assert info(original)==item['raw'] and info(candidate)==item['candidate'],item['raw_path']
 assert candidate==original.replace(prefix,b'<LOCAL_HOME>'),item['raw_path']
outer=json.loads((base/'PUBLIC_OUTER_ALLOWLIST.json').read_text())['files']
for path,value in outer.items():assert info((base/path).read_bytes())==value,path
lines=(base/'SHA256SUMS').read_text().splitlines()
for line in lines:
 sha,path=line.split('  ',1);assert hashlib.sha256((base/path).read_bytes()).hexdigest()==sha,path
print(json.dumps({'status':'PASS','raw_count':len(raw),'candidate_count':len(safe),'outer_count':len(outer),'sum_count':len(lines),'transformation':'exact declared home prefix only'}))
