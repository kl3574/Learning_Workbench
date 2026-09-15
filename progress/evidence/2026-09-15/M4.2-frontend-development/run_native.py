import datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('<REPOSITORY_ROOT>');out=pathlib.Path('<ACCEPTANCE_CACHE>/m42-frontend')
name=sys.argv[1];command=sys.argv[2:]
def inventory():
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(set(paths)) if name and (root/name).is_file() and not name.startswith(('progress/','docs/ui/','docs/adr/'))}
record={'scope':'developmental own RestartRuntime native; source drift is explicitly recorded; no M4.2 acceptance claim','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cwd':str(root),'command':command,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'sources_before':inventory(),'config_path':command[command.index('--config')+1], 'config_sha256':hashlib.sha256(pathlib.Path(command[command.index('--config')+1]).read_bytes()).hexdigest(), 'config_source':pathlib.Path(command[command.index('--config')+1]).read_text()}
source_copy=out/(name+'-source-inputs');source_copy.mkdir(exist_ok=False)
for source,expected in record['sources_before'].items():
    if source.startswith('apps/web/src/features/recommendations/') or source.startswith('tests/e2e/recommendations') or source in ('apps/web/src/workbench/Shell.tsx','apps/web/src/shared/createResponseDraftJournal.ts','apps/web/src/features/routes/RouteDirectory.tsx','tests/e2e/restartRuntime.ts','packages/contracts/generated/api-types.ts','packages/contracts/generated/api-client.ts'):
        body=(root/source).read_bytes();assert hashlib.sha256(body).hexdigest()==expected
        target=source_copy/(source+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
record['source_input_copies']=str(source_copy)
result=subprocess.run(command,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/f'{name}.log').write_text(result.stdout)
record.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,output_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),sources_after=inventory())
record['source_changes_during_run']=[p for p in sorted(set(record['sources_before'])|set(record['sources_after'])) if record['sources_before'].get(p)!=record['sources_after'].get(p)]
(out/f'{name}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));print(result.stdout);print(json.dumps({'receipt':str(out/f'{name}.json'),'exit_code':result.returncode,'source_changes_during_run':record['source_changes_during_run']}));sys.exit(result.returncode)
