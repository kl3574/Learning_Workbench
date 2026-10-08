"""Private acceptance: real pinned CLI, own stable Broker, no thread or model."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03')
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from services.api.app.main import create_app
from services.api.app.config import Settings
from services.api.app.security import issue_bootstrap_code
from services.api.app.infrastructure import codex_probe
BINARY=Path('$HOME/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl/bin/codex')
DATA=Path('$HOME/.cache/m63-capability-actual-broker')
settings=Settings(data_dir=DATA,codex_executable=BINARY)
app=create_app(settings)
database=app.state.database;database.initialize()
client=TestClient(app,base_url=settings.origin)
real_popen=codex_probe.subprocess.Popen
spawns=[]
def observed_popen(arguments,**kwargs):
    assert kwargs['close_fds'] and kwargs['start_new_session'] and len(kwargs['pass_fds'])==1
    assert set(kwargs['env'])=={'PATH','HOME','CODEX_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','TMPDIR','LANG','TOKIO_WORKER_THREADS'}
    assert kwargs['env']['CODEX_HOME']==str(DATA/'codex-broker'/'home')
    spawns.append(True)
    return real_popen(arguments,**kwargs)
codex_probe.subprocess.Popen=observed_popen
assert client.get('/api/v1/codex/capabilities').status_code==401 and not spawns
bootstrap=client.post('/api/v1/session/bootstrap',json={'one_time_code':issue_bootstrap_code(database)},headers={'Origin':settings.origin})
assert bootstrap.status_code==200
with database.connect() as connection: before='\n'.join(connection.iterdump()).encode()
first=client.get('/api/v1/codex/capabilities')
assert first.status_code==200
assert first.json()==codex_probe.project_capabilities({'codexHome':'synthetic-private-placeholder','platformFamily':'unix','platformOs':'linux','userAgent':'codex_cli_rs/0.160.0'},{'account':None,'requiresOpenaiAuth':True,'workspaceRouting':None})
assert 'no-store' in first.headers['cache-control']
home=DATA/'codex-broker'/'home'
identity=(home.stat().st_dev,home.stat().st_ino)
second=client.get('/api/v1/codex/capabilities')
assert second.status_code==200 and second.content==first.content
assert (home.stat().st_dev,home.stat().st_ino)==identity and len(spawns)==2
config=home/'config.toml'
assert config.read_bytes()==codex_probe.CONFIG
try:
    config.write_bytes(b'[features]\nhooks = true\n')
    unknown=client.get('/api/v1/codex/capabilities')
    assert unknown.status_code==503 and unknown.json()['error']['code']=='CODEX_BROKER_CONFIG_CHANGED'
    assert len(spawns)==2 and 'authorized' not in unknown.json()
finally:
    config.write_bytes(codex_probe.CONFIG)
with database.connect() as connection: after='\n'.join(connection.iterdump()).encode()
assert before==after
print(json.dumps({'status':'PASS','source_kind':'actual_fixed_cli_control_over_real_http_application','binary_sha256':codex_probe.PINNED_SHA256,'projection':first.json(),'unauthenticated_status':401,'positive_reads':2,'same_broker_identity':True,'owned_subprocess_count':len(spawns),'changed_config_status':unknown.status_code,'changed_config_code':unknown.json()['error']['code'],'business_database_unchanged':before==after,'business_database_before_sha256':hashlib.sha256(before).hexdigest(),'business_database_after_sha256':hashlib.sha256(after).hexdigest(),'raw_handshake_account_stderr_retained':False,'thread_turn_login_model_calls':0},ensure_ascii=False,sort_keys=True))
