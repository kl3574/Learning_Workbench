from pathlib import Path
import hashlib,importlib.util,json,os,re
base=Path(__file__).resolve().parent
root=Path('$HOME/.cache/learning-workbench-acceptance/m71-backup-session-history-oct03')
sha=lambda data:hashlib.sha256(data).hexdigest()
# Immutable private originals; no following pytest's convenience symlinks.
raw=[]
for directory,children,files in os.walk(base,followlinks=False):
    children[:]=sorted(name for name in children if name not in {'safe-share','tmp'} and not (Path(directory)/name).is_symlink())
    for name in sorted(files):
        path=Path(directory)/name
        if path.is_symlink() or path.name in {'RAW_MANIFEST.json','SAFE_SHARE.json','SAFE_SCAN.json','FINAL_HASHES.json'}: continue
        data=path.read_bytes();raw.append({'path':str(path.relative_to(base)),'bytes':len(data),'sha256':sha(data)})
(base/'RAW_MANIFEST.json').write_text(json.dumps({'private_only':True,'scope':'Original private files, including synthetic DBs/ZIPs; never an upload allowlist','files':raw},indent=2,sort_keys=True)+'\n')
# Concrete top-level evidence + exact safe control filenames in the two final real-CLI phases.
names=['REPORT.md','SOURCE.json','FIXED_RECEIPT.json','CASCADE_READBACK.json','EARLY_EXECUTIONS.json','production.patch','capture_source.py','seal.py','cascade-readback-attempt-01.json','11-import-fixture-readonly.json']
for name in ['01-red','02-green','03-readback-diagnostic','04-green','05-owners','06-owners','08-final-red','09-final-focused','11-fixed-related','13-single-diagnostic']:
    names += [name+'.log',name+'.exit']
names += ['07-ruff.log','07-ruff.exit','10-static.log','10-static.exit','12-fixed-static.log','12-fixed-static.json','08-red-tracked-source.json','11-fixed-before.json','11-fixed-after.json','01-red-test.py']
for phase in ['08-final-red-data','11-fixed-related-data']:
    for case in sorted((base/phase).iterdir()):
        if not case.is_dir() or case.is_symlink() or not (case/'backup-cli-receipt.json').is_file(): continue
        for name in ['backup-cli.stdout','backup-cli.stderr','backup-cli-receipt.json']:
            names.append(str((case/name).relative_to(base)))
spec=importlib.util.spec_from_file_location('scanner',root/'scripts/check_publication.py')
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
items=[];failures=[]
header=re.compile(rb'(?im)^\s*(?:[<>]\s*)?(?:authorization|cookie|set-cookie|x-csrf-token)\s*:\s*\S+')
for name in names:
    path=base/name;data=path.read_bytes();public=data.replace(b'$HOME',b'$HOME')
    destination=base/'safe-share'/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(public)
    findings=scanner.inspect('progress/evidence/M7.1-backup-session/'+name,public)
    if header.search(public): findings.append('raw authentication header-like line')
    if findings:failures.append({'path':name,'reasons':findings})
    items.append({'source':name,'public_path':'safe-share/'+name,'raw_sha256':sha(data),'public_sha256':sha(public),'raw_bytes':len(data),'public_bytes':len(public),
                  'transformation':'exact_home_prefix_only' if data!=public else 'none'})
(base/'SAFE_SHARE.json').write_text(json.dumps({'scope':'Only these exact files are candidates; no database, ZIP, secret store or arbitrary pytest-data files','transformation':{'from':'$HOME','to':'$HOME'},'count':len(items),'files':items},indent=2,sort_keys=True)+'\n')
scan={'candidate_count':len(items),'scanner_source_sha256':sha((root/'scripts/check_publication.py').read_bytes()),'credential_path_scanner_and_header_findings':failures,'status':'PASS' if not failures else 'FAIL'}
(base/'SAFE_SCAN.json').write_text(json.dumps(scan,indent=2,sort_keys=True)+'\n')
keys=['REPORT.md','SOURCE.json','FIXED_RECEIPT.json','CASCADE_READBACK.json','RAW_MANIFEST.json','SAFE_SHARE.json','SAFE_SCAN.json']
final={'head':'b6340d913df252e30b920ec548e6cfd580505ec9','raw_count':len(raw),'safe_count':len(items),'hashes':{name:sha((base/name).read_bytes()) for name in keys}}
(base/'FINAL_HASHES.json').write_text(json.dumps(final,indent=2,sort_keys=True)+'\n')
print(json.dumps({'raw_count':len(raw),'safe_count':len(items),'scan_status':scan['status'],'finding_count':len(failures),'hashes':final['hashes']}))
if failures: raise SystemExit(1)
