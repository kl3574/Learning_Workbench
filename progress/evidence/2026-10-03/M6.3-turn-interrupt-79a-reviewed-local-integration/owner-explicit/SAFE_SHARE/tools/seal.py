"""Seal an explicit evidence set; runtime directories are never candidates."""
from pathlib import Path
import hashlib,importlib.util,json,sys
base=Path(sys.argv[1]); scanner=Path(sys.argv[2])
spec=importlib.util.spec_from_file_location('publication_scanner',scanner); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
def info(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def write(name,value):
 p=base/name; assert not p.exists(),name; p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
paths=['REPORT.md','SOURCE_BINDING.json','SOURCE_BINDING_HARNESS_FAILURE.json','tools/run_stage.py','tools/source_binding.py','tools/seal.py','tools/verify.py']
paths += ['red-cc2cc675/'+f for f in ['run.py','run.log','receipt.json','before.json','after.json']]
paths += ['dev-01/'+f for f in ['runner.sh','run.log','exit.txt','inputs-before.json','inputs-after.json','source.patch','head.txt','mypy.log']]
paths += ['boundaries-1b49/'+f for f in ['runner.py','inputs-before.json','HARNESS_FAILURE.json']]
for stage in ['boundaries-1b49-02','related-79a3','ruff-79a3','mypy-79a3','generated-79a3','spec-79a3','ts-79a3']:
 paths += [stage+'/'+f for f in ['runner.py','run.log','receipt.json','inputs-before.json','inputs-after.json']]
raw={name:info((base/name).read_bytes()) for name in paths}
assert len(raw)==len(paths)
write('RAW_MANIFEST.json',{'schema':'interrupt-evidence-raw-v1','files':raw,'exclusions':['all basetemp/tmp/cache/runtime DB and credentials','safe derivatives and outer metadata'], 'scope':'Complete explicitly listed deliverable evidence, not a filesystem or database export.'})
# Construct the literal prefix from bytes so this script remains identical under
# the same declared transformation; no secondary path substitution is hidden.
prefix=bytes([47,104,111,109,101,47,108,107,120])
replacement=b'<LOCAL_HOME>'
files=[]; failures=[]
for name in paths:
 data=(base/name).read_bytes(); candidate=data.replace(prefix,replacement)
 target=base/'SAFE_SHARE'/name; target.parent.mkdir(parents=True,exist_ok=True); assert not target.exists(); target.write_bytes(candidate)
 findings=module.inspect('progress/evidence/interrupt/'+name,candidate)
 if findings: failures.append({'path':name,'findings':findings})
 files.append({'raw_path':name,'candidate_path':'SAFE_SHARE/'+name,'raw':info(data),'candidate':info(candidate),'transformation':'exact home prefix to <LOCAL_HOME> only','scanner_findings':findings})
write('CANDIDATE_SCAN.json',{'scanner_sha256':info(scanner.read_bytes())['sha256'],'count':len(files),'findings':failures,'manual_scope':'Synthetic source/commands/logs/maps only. No database, archive, raw account/CLI response, cookie/CSRF value or environment export.'})
assert not failures,failures
write('SAFE_SHARE.json',{'schema':'interrupt-safe-share-v1','source_head':'79a3c0da4bef9d948bcd6a969a25ff55fd5833a0','files':files,'scanner_sha256':info(scanner.read_bytes())['sha256'],'excluded':'Every path absent from files is not approved for sharing by this descriptor.'})
# Every outer file is itself ordinary scanner-checked metadata.
outer=['RAW_MANIFEST.json','SAFE_SHARE.json','CANDIDATE_SCAN.json']
for name in outer: assert not module.inspect('progress/evidence/interrupt/'+name,(base/name).read_bytes())
write('PUBLIC_OUTER_ALLOWLIST.json',{'schema':'interrupt-outer-v1','files':{n:info((base/n).read_bytes()) for n in outer}})
sums=paths+['SAFE_SHARE/'+n for n in paths]+outer+['PUBLIC_OUTER_ALLOWLIST.json']
(base/'SHA256SUMS').write_text(''.join(info((base/n).read_bytes())['sha256']+'  '+n+'\n' for n in sums))
# Immediate complete readback, using manifest content and the declared transform.
for entry in files:
 original=(base/entry['raw_path']).read_bytes(); candidate=(base/entry['candidate_path']).read_bytes()
 assert info(original)==entry['raw'] and info(candidate)==entry['candidate']
 assert candidate==original.replace(prefix,replacement)
for name,value in json.loads((base/'PUBLIC_OUTER_ALLOWLIST.json').read_text())['files'].items():assert info((base/name).read_bytes())==value
print(json.dumps({'raw':len(raw),'safe':len(files),'outer':len(outer),'checksums':len(sums),'status':'PASS'}))
