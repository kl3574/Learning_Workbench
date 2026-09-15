from pathlib import Path
import datetime,hashlib,json,subprocess,sys
base=Path('<DIAGNOSIS_CACHE>');root=base/'fixed-source-01';name=sys.argv[1];command=sys.argv[2:]
manifest=json.loads((base/'fixed-source-01-manifest.json').read_text())
def inventory(): return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in manifest['files']}
before=inventory();record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(root),'source_manifest_sha256':hashlib.sha256((base/'fixed-source-01-manifest.json').read_bytes()).hexdigest(),'command':command,'sources_before':before,'harness':{str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (base/'fixed-harness-01').glob('*') if p.is_file()}}
result=subprocess.run(command,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(base/(name+'.log')).write_text(result.stdout);after=inventory()
record.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),sources_after=after,source_changes=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)])
(base/(name+'.json')).write_text(json.dumps(record,indent=2));print(result.stdout);print(json.dumps({'exit_code':result.returncode,'receipt':str(base/(name+'.json')),'source_changes':record['source_changes']}));sys.exit(result.returncode)
