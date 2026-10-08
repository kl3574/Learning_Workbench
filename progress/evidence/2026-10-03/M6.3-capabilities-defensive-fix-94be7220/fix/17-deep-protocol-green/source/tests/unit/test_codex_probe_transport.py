"""Real child pipes with synthetic protocol peers; these are not CLI acceptance."""
import os
import subprocess
import sys

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure import codex_probe


@pytest.mark.parametrize('mode,code', [('success', None), ('timeout', 'CODEX_PROBE_TIMEOUT'),
    ('duplicate', 'CODEX_PROTOCOL_INVALID'), ('flood', 'CODEX_PROTOCOL_INVALID'),
    ('wrong_id', 'CODEX_PROTOCOL_INVALID'), ('eof', 'CODEX_PROBE_UNAVAILABLE'),
    ('deep_json', 'CODEX_PROTOCOL_INVALID')])
def test_bounded_control_transport_kills_and_reaps_owned_child(tmp_path, monkeypatch, mode, code):
    (tmp_path / 'workspace').mkdir()
    observed, children = [], []
    real_popen = subprocess.Popen
    script = '''
import json,os,sys,time
mode=sys.argv[1]
request=json.loads(sys.stdin.readline())
assert request['method']=='initialize' and request['id']==1
assert request['params']['capabilities']['experimentalApi'] is False
if mode=='timeout': time.sleep(60)
if mode=='flood': os.write(2,b'synthetic_private_error'*4000); time.sleep(60)
if mode=='eof': sys.exit(0)
if mode=='duplicate': print('{"id":9,"id":1,"result":{}}',flush=True); time.sleep(60)
if mode=='wrong_id': print('{"id":3,"result":{}}',flush=True); time.sleep(60)
if mode=='deep_json': print('{"id":1,"result":'+'['*2000+']'*2000+'}',flush=True); time.sleep(60)
print(json.dumps({'id':1,'result':{'codexHome':'/synthetic/private','platformFamily':'unix','platformOs':'linux','userAgent':'codex_cli_rs/0.160.0'}}),flush=True)
assert json.loads(sys.stdin.readline())=={'method':'initialized','params':{}}
assert json.loads(sys.stdin.readline())=={'id':2,'method':'account/read','params':{'refreshToken':False}}
print(json.dumps({'id':2,'result':{'account':None,'requiresOpenaiAuth':True,'workspaceRouting':None}}),flush=True)
time.sleep(60)
'''
    def launch(arguments, **kwargs):
        observed.append((arguments, kwargs))
        child = real_popen([sys.executable, '-I', '-S', '-c', script, mode], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(codex_probe.subprocess, 'Popen', launch)
    monkeypatch.setattr(codex_probe, 'PROBE_SECONDS', 0.5)
    descriptor = os.open('/dev/null', os.O_RDONLY)
    try:
        probe = codex_probe.LocalCodexProbe(tmp_path)
        if code:
            with pytest.raises(ApiError) as error:
                probe._observe(descriptor, tmp_path)
            assert error.value.code == code
            assert 'synthetic' not in str(error.value)
        else:
            result = probe._observe(descriptor, tmp_path)
            assert result['available'] and result['authorized'] is False
        arguments, options = observed[0]
        assert arguments[-2:] == [str(descriptor), str(tmp_path)]
        assert options['close_fds'] and options['start_new_session']
        assert options['pass_fds'] == (descriptor,)
        assert options['env']['CODEX_HOME'] == str(tmp_path / 'home')
        assert set(options['env']) == {'PATH','HOME','CODEX_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','TMPDIR','LANG','TOKIO_WORKER_THREADS'}
        assert children[0].poll() is not None
        assert children[0].stdin.closed and children[0].stdout.closed and children[0].stderr.closed
        with pytest.raises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)
    finally:
        os.close(descriptor)
