"""Owned FIFO damage control only; no real Codex process or config read."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,time

program=r'''
import json,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe import LocalCodexProbe
from services.api.app.application.errors import ApiError
try: LocalCodexProbe(Path(sys.argv[1]),Path(sys.argv[2])).read()
except ApiError as e:print(json.dumps({'code':e.code,'status':e.status}),flush=True)
'''
with tempfile.TemporaryDirectory(prefix='fifo-',dir='$HOME/.cache/lw-cir') as td:
    base=Path(td);data=base/'data';home=data/'codex-broker'/'home';home.mkdir(parents=True,mode=0o700)
    data.chmod(0o700);home.parent.chmod(0o700)
    binary=base/'dummy';binary.write_bytes(b'not executed')
    fifo=home/'config.toml';os.mkfifo(fifo,0o600)
    child=subprocess.Popen([sys.executable,'-c',program,str(data),str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        cwd='$HOME/.cache/learning-workbench-acceptance/m63-capabilities-independent-review-tree-oct03',
        env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},close_fds=True)
    time.sleep(0.5)
    pending=child.poll() is None
    writer=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK) if pending else None
    try:
        stdout,stderr=child.communicate(timeout=2)
        print(json.dumps({'pending_before_external_writer':pending,'child_exit':child.returncode,'result':json.loads(stdout) if stdout else None}))
    finally:
        if writer is not None:os.close(writer)
        if child.poll() is None:child.kill();child.wait()
