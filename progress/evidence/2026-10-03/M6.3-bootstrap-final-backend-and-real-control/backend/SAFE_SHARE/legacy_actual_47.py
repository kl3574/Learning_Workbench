"""Read earlier real unknown facts with the new decoder; no process may start."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-implementation-oct03')
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code
OUT=Path(__file__).parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
original_popen=subprocess.Popen
def forbidden(*args,**kwargs): raise AssertionError('historical read started a process')
subprocess.Popen=forbidden
results=[]
def owner_facts(app):
    with app.state.database.connect() as connection:
        connection.execute('PRAGMA query_only=ON')
        names=[row['name'] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'codex_%' ORDER BY name")]
        assert len(names)==8
        return {name:hashlib.sha256(json.dumps([tuple(row) for row in connection.execute('SELECT * FROM '+name+' ORDER BY rowid')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for name in names}
try:
    for number in (32,33,34):
        previous=json.loads((OUT/f'actual-{number}/actual.json').read_text())
        settings=Settings(data_dir=OUT/f'actual-{number}/private-workspace',codex_executable=Path('/synthetic/absent-cli'))
        app=create_app(settings);app.state.database.initialize()
        before=owner_facts(app)
        client=TestClient(app,base_url=settings.origin)
        auth=client.post('/api/v1/session/bootstrap',json={'one_time_code':issue_bootstrap_code(app.state.database)},headers={'Origin':settings.origin})
        assert auth.status_code==200
        prep=client.get('/api/v1/codex/session-preparations/'+previous['preparation_ack']['id'])
        session=client.get('/api/v1/codex/sessions/'+previous['session_current']['id'])
        assert prep.status_code==session.status_code==200
        assert prep.json()==previous['consumed_preparation'] and session.json()==previous['session_current']
        assert session.json()['status']=='unknown'
        assert before==owner_facts(app)
        results.append({'original_stage':number,'preparation':prep.json(),'session':session.json(),'eight_owner_tables_unchanged':True})
finally:
    subprocess.Popen=original_popen
receipt={'source_head':head,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'scope':'new actor reads original real v2 unknown facts through v3; original actors and all eight owner tables unchanged; no CLI',
         'status':'PASS','instances':results}
(OUT/'legacy-actual-47.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','historical_instances':len(results),'cli_starts':0}))
