import hashlib,json,pathlib,subprocess,sys,datetime
root=pathlib.Path('$HOME/.cache/learning-workbench-acceptance/m62-note-reanchor-native-oct02')
evidence=pathlib.Path(__file__).parent
name,*command=sys.argv[1:]
dest=evidence/name
dest.mkdir(exist_ok=False)
def source():
 names=subprocess.check_output(['git','ls-files','-co','--exclude-standard'],cwd=root,text=True).splitlines()
 return [{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest(),'bytes':(root/p).stat().st_size} for p in sorted(set(names)) if (root/p).is_file() and not p.startswith('progress/')]
before=source();(dest/'before.json').write_text(json.dumps(before,indent=2)+'\n')
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (dest/'run.log').open('wb') as log:r=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
after=source();(dest/'after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt={'command':command,'cwd':str(root),'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'input_count':len(before),'unchanged':before==after,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'status':subprocess.check_output(['git','status','--short'],cwd=root,text=True),'log_sha256':hashlib.sha256((dest/'run.log').read_bytes()).hexdigest(),'before_sha256':hashlib.sha256((dest/'before.json').read_bytes()).hexdigest(),'after_sha256':hashlib.sha256((dest/'after.json').read_bytes()).hexdigest()}
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print((dest/'run.log').read_text()[-7000:]);print(json.dumps({'stage':name,'exit_code':r.returncode,'inputs':len(before),'unchanged':before==after}))
sys.exit(r.returncode)
