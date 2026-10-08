"""Real local kernel fences; no CLI account, model or external request."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_local_probe_child_cannot_read_outside_or_create_any_network_socket(tmp_path):
    broker = tmp_path / 'broker'; broker.mkdir()
    inside = broker / 'inside'; inside.write_text('allowed')
    outside = tmp_path / 'outside'; outside.write_text('SYNTHETIC_OUTSIDE')
    program = """
import json,os,socket,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
broker,inside,outside=sys.argv[1:]
restrict_probe(Path(sys.executable),Path(broker))
result={'inside':Path(inside).read_text(),'outside_denied':False,'sockets_denied':[]}
try: Path(outside).read_text()
except PermissionError: result['outside_denied']=True
for family in (socket.AF_INET,socket.AF_INET6,socket.AF_UNIX):
 try: socket.socket(family,socket.SOCK_STREAM)
 except PermissionError: result['sockets_denied'].append(True)
 else: result['sockets_denied'].append(False)
print(json.dumps(result))
"""
    run = subprocess.run([sys.executable, '-c', program, str(broker), str(inside), str(outside)],
                         cwd=Path(__file__).parents[2], capture_output=True, timeout=5,
                         env={'PATH':os.defpath, 'PYTHONDONTWRITEBYTECODE':'1'})
    assert run.returncode == 0, run.stderr.decode()[-2000:]
    assert json.loads(run.stdout) == {'inside':'allowed','outside_denied':True,'sockets_denied':[True,True,True]}
