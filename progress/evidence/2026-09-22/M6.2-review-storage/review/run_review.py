from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).resolve().parent
python = '<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python'
receipts=[]
for label, tree, argv in [
    ('original-relations', 'source', [python, str(base / 'probe_relations.py'), str(base / 'source')]),
    ('fixed-relations', 'fixed', [python, str(base / 'probe_relations.py'), str(base / 'fixed')]),
    ('fixed-storage-tests', 'fixed', [python, '-m', 'pytest', '-q', 'tests/integration/test_review_storage_constraints.py', 'tests/integration/test_review_storage_migration.py']),
]:
    cwd = base / tree
    started = datetime.now(UTC).isoformat()
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=cwd,text=True).strip()
    paths = subprocess.check_output(['git','ls-files'], cwd=cwd,text=True).splitlines()
    before = {p:hashlib.sha256((cwd/p).read_bytes()).hexdigest() for p in paths if (cwd/p).is_file()}
    run = subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log = base / (label + '.log')
    log.write_bytes(run.stdout)
    after = {p:hashlib.sha256((cwd/p).read_bytes()).hexdigest() for p in paths if (cwd/p).is_file()}
    assert before==after
    receipt = {'label':label,'head':head,'argv':argv,'started_at':started,'ended_at':datetime.now(UTC).isoformat(),
        'exit_code':run.returncode,'log_sha256':hashlib.sha256(run.stdout).hexdigest(),'source_file_count':len(before),'source_unchanged':True}
    (base/(label+'.source.json')).write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
    (base/(label+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    receipts.append(receipt)
    print(json.dumps(receipt), flush=True)
    print(run.stdout.decode()[-1800:], flush=True)
(base/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
