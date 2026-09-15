from pathlib import Path
import datetime,hashlib,json,subprocess,sys
root=Path('<ACCEPTANCE_CACHE>/m42-4cf13f7');out=Path('<DIAGNOSIS_CACHE>');name=sys.argv[1];command=sys.argv[2:]
def inventory():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sorted(paths) if p and (root/p).is_file() and not p.startswith(('progress/','docs/ui/','docs/adr/'))}
before=inventory();record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(root),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'command':command,'sources_before':before,'observer_sha256':hashlib.sha256((out/'observer-controlled.ts').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256((out/'routes-controlled.spec.ts').read_bytes()).hexdigest()}
result=subprocess.run(command,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(name+'.log')).write_text(result.stdout);after=inventory()
record.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),sources_after=after,source_changes=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)])
(out/(name+'.json')).write_text(json.dumps(record,indent=2));print(result.stdout);print(json.dumps({'exit_code':result.returncode,'receipt':str(out/(name+'.json')),'source_changes':record['source_changes']}));sys.exit(result.returncode)
