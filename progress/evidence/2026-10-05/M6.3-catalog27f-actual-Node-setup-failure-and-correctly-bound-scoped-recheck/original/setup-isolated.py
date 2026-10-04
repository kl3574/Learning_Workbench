from pathlib import Path
import subprocess,hashlib,json,datetime,tarfile,shutil
O=Path(__file__).resolve().parent;B=O.parent
R=B/'m62-public-safe-oct02';T=B/'m63-catalog27f-locked-node-environment-oct05'
HEAD='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def run(name,argv,cwd):
 put(name+'-command.json',{'argv':argv,'cwd':str(cwd),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 with (O/(name+'.log')).open('wb') as out:x=subprocess.run(argv,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
 raw=(O/(name+'.log')).read_bytes();put(name+'-receipt.json',{'exit_code':x.returncode,'log_bytes':len(raw),'log_sha256':sha(raw),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(name,x.returncode)
assert not T.exists()
run('worktree',['git','worktree','add','-b','feat/M6.3-catalog27f-locked-node-env-oct05',str(T),HEAD],R)
# Reuse only the exact public Node archive pinned by existing setup.py, never user config or profiles.
a=R/'.toolchain/node-v24.21.0-linux-x64.tar.xz';reuse={'archive_exists':a.exists()}
if a.exists():
 raw=a.read_bytes();reuse.update({'archive_size':len(raw),'archive_sha256':sha(raw)})
 assert sha(raw)=='fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6'
 dest=T/'.toolchain';dest.mkdir(exist_ok=False);target=dest/a.name;target.write_bytes(raw)
 with tarfile.open(target) as src:src.extractall(dest,filter='data')
 reuse['action']='Exact pinned cached public Node archive extracted locally; no runtime profile/credentials copied'
else:reuse['action']='Existing make setup installer will fetch only its pinned public archive'
put('NODE_ARCHIVE_REUSE.json',reuse)
run('locked-setup',['make','setup'],T)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=T).decode().strip()==HEAD
assert not subprocess.check_output(['git','status','--porcelain'],cwd=T)
put('SETUP_READBACK.json',{'source':HEAD,'tree':str(T),'setup_exit_code':0,'tracked_source_unchanged_clean':True,'production_code_edit':False,'original_fullsuite_tree_environment_unchanged':True,'actual_models':0,'purpose':'Fresh isolated locked environment for original Node version requirement failure; not product behavioral repair or complete-suite qualification'})
print('New isolated locked setup complete; source unchanged, original fullsuite environment untouched.')
