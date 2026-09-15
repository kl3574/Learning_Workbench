import datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('<REPOSITORY_ROOT>')
out=pathlib.Path('<ACCEPTANCE_CACHE>/m42-frontend')
name=sys.argv[1]; command=sys.argv[2:]
paths=list((root/'apps/web/src/features/recommendations').glob('*'))+[root/'apps/web/src/workbench/Shell.tsx',root/'apps/web/src/features/routes/RouteDirectory.tsx',root/'packages/contracts/generated/api-types.ts',root/'packages/contracts/generated/api-client.ts',root/'apps/web/src/shared/createResponseDraftJournal.ts']
def inventory():return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cwd':str(root),'command':command,'sources_before':inventory()}
result=subprocess.run(command,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/f'{name}.log').write_text(result.stdout)
record.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=result.returncode,output_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),sources_after=inventory())
(out/f'{name}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(result.stdout)
print(json.dumps({'receipt':str(out/f'{name}.json'),'exit_code':result.returncode}))
sys.exit(result.returncode)
