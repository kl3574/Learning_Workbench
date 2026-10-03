from pathlib import Path
import hashlib,json,re,sys
E=Path(__file__).parent
R=Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03')
sys.path.insert(0,str(R))
from scripts.check_publication import inspect
sha=lambda x:hashlib.sha256(x).hexdigest()
files=sorted(p for p in E.rglob('*') if p.is_file() and p.name not in {'MANIFEST.json','SAFE_SHARE.json','SCAN.json'})
raw=[];allow=[];findings=[]
headers=re.compile(rb'(?im)(?:authorization\s*[:=]\s*["\x27]?\s*(?:bearer|basic)\s+[A-Za-z0-9+/_=-]{12,}|(?:x-csrf-token|cookie|set-cookie)\s*[:=]\s*["\x27]?[A-Za-z0-9_=-]{20,})')
for p in files:
 name=p.relative_to(E).as_posix();data=p.read_bytes()
 raw.append({'path':name,'size':len(data),'sha256':sha(data)})
 if 'pytest-of-lkx' in p.parts: continue
 public=data.replace(b'$HOME',b'$HOME')
 problems=inspect('progress/evidence/2026-10-03/M6.3-codex-ipc-fix/'+name,public)
 if headers.search(public):problems.append('possible actual credential header value')
 if problems:findings.append({'path':name,'issues':problems})
 else:allow.append({'path':name,'raw_sha256':sha(data),'public_sha256':sha(public),'public_size':len(public),'transform':'exact $HOME -> $HOME' if public!=data else 'identity'})
manifest={'scope':'Original evidence files; excludes only self manifest/share/scan to avoid circularity','files':raw}
(E/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
data=(E/'MANIFEST.json').read_bytes();public=data.replace(b'$HOME',b'$HOME')
assert not inspect('progress/evidence/2026-10-03/M6.3-codex-ipc-fix/MANIFEST.json',public)
allow.append({'path':'MANIFEST.json','raw_sha256':sha(data),'public_sha256':sha(public),'public_size':len(public),'transform':'identity'})
scan={'status':'PASS' if not findings else 'FAIL','scanned_candidates':len(allow)+len(findings),'raw_manifest_entries':len(raw),'findings':findings,'scanner_source':{'path':'scripts/check_publication.py','sha256':sha((R/'scripts/check_publication.py').read_bytes())},'additional_check':'Actual Authorization bearer/basic and Cookie/Set-Cookie/X-CSRF header value patterns','only_transform':'exact $HOME -> $HOME'}
(E/'SCAN.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2)+'\n')
data=(E/'SCAN.json').read_bytes();allow.append({'path':'SCAN.json','raw_sha256':sha(data),'public_sha256':sha(data),'public_size':len(data),'transform':'identity'})
share={'scope':'Explicit safe candidates only; does not authorize automatic publication','raw_manifest_sha256':sha((E/'MANIFEST.json').read_bytes()),'only_transform':'exact $HOME -> $HOME','forbidden':'Do not copy runtime Broker/TMPDIR/database/dependencies/global credentials or new files outside this list','files':allow}
(E/'SAFE_SHARE.json').write_text(json.dumps(share,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'raw_count':len(raw),'candidate_count':len(allow),'findings':findings,'report_sha256':sha((E/'REPORT.md').read_bytes()),'manifest_sha256':sha((E/'MANIFEST.json').read_bytes()),'safe_share_sha256':sha((E/'SAFE_SHARE.json').read_bytes()),'scan_sha256':sha((E/'SCAN.json').read_bytes())},ensure_ascii=False))
assert not findings
