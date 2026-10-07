from pathlib import Path
import datetime,hashlib,json,subprocess,sys
o=Path(__file__).resolve().parent
assert not (o/'root-receipt.json').exists()
def sha(b):return hashlib.sha256(b).hexdigest()
argv=['python3',str(o/'sync.py')]
(o/'root-command.json').write_text(json.dumps({'argv':argv,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha((o/'sync.py').read_bytes())},indent=2)+'\n')
x=subprocess.run(argv,capture_output=True)
(o/'root.stdout').write_bytes(x.stdout);(o/'root.stderr').write_bytes(x.stderr)
(o/'root-receipt.json').write_text(json.dumps({'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
print(x.stdout.decode(),end='');print('actual_exit',x.returncode)
sys.exit(x.returncode)
