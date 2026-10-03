"""Real pipes and synthetic protocol peers, never actual CLI/model acceptance."""
import os
import subprocess
import sys
import time

import pytest

from services.api.app.infrastructure import codex_bootstrap_runtime as module


@pytest.mark.parametrize('mode,status', [('ready', 'ready'), ('init_eof', 'failed'), ('init_timeout', 'failed'),
    ('init_identity', 'failed'), ('result_eof', 'unknown'), ('result_timeout', 'unknown'), ('wrong_id', 'unknown'),
    ('duplicate_key', 'unknown'), ('duplicate_response', 'unknown'), ('flood', 'unknown'), ('wrong_root', 'unknown'),
    ('unexpected_request', 'unknown'), ('deep_json', 'unknown'), ('unknown_member', 'unknown'),
    ('tail_duplicate', 'unknown'), ('tail_notification', 'unknown'), ('tail_stderr', 'unknown'),
    ('slow_launch', 'failed'), ('reap_unverified', 'unknown')])
def test_exact_three_frames_bounded_responses_and_complete_cleanup(tmp_path, monkeypatch, mode, status):
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'absent-cli')
    frozen = runtime.freeze('workspace_default')
    real_popen = subprocess.Popen
    children, options = [], []
    peer = '''
import json,os,sys,time
mode=sys.argv[1]
first=json.loads(sys.stdin.readline())
assert first['method']=='initialize' and first['id']==1
if mode=='init_eof': sys.exit(0)
if mode=='init_timeout': time.sleep(60)
initialized={'codexHome':os.environ['CODEX_HOME'],'platformFamily':'unix','platformOs':'linux','userAgent':'codex_cli_rs/0.160.0'}
if mode=='init_identity': initialized['codexHome']='/synthetic/wrong-broker'
print(json.dumps({'id':1,'result':initialized}),flush=True)
assert json.loads(sys.stdin.readline())=={'method':'initialized','params':{}}
start=json.loads(sys.stdin.readline())
assert start['method']=='thread/start' and start['id']==2
assert start['params']['approvalPolicy']=='never' and start['params']['sandbox']=='read-only'
assert start['params']['baseInstructions']==start['params']['developerInstructions']==''
if mode=='result_eof': sys.exit(0)
if mode=='result_timeout': time.sleep(60)
if mode=='duplicate_key': print('{"id":2,"id":2,"result":{}}',flush=True);time.sleep(60)
if mode=='flood': os.write(2,b'synthetic_stderr'*6000);time.sleep(60)
if mode=='unexpected_request': print(json.dumps({'id':17,'method':'item/commandExecution/requestApproval','params':{}}),flush=True);time.sleep(60)
if mode=='deep_json': print('{"id":2,"result":'+'['*16000+']'*16000+'}',flush=True);time.sleep(60)
cwd=start['params']['cwd']
thread={'cliVersion':'0.160.0','createdAt':0,'cwd':cwd,'ephemeral':False,'id':'synthetic-thread-id',
 'modelProvider':'openai','preview':'','projectId':None,'sessionId':'synthetic-session-id','source':'appServer',
 'status':{'type':'idle'},'turns':[],'updatedAt':0}
result={'approvalPolicy':'never','approvalsReviewer':'user','cwd':cwd,'model':start['params']['model'],
 'modelProvider':'openai','sandbox':{'type':'readOnly','networkAccess':False},'thread':thread}
if mode=='wrong_root': result['cwd']='/synthetic/other-root'
if mode=='unknown_member': result['extra_unverified_fact']=True
if mode=='tail_stderr': result['thread']['name']='x'*60000
response={'id':9 if mode=='wrong_id' else 2,'result':result}
line=json.dumps(response)+'\\n'
if mode=='tail_stderr':
    os.write(1,line[:-1].encode())
    os.write(2,b'x'*8192)
    os.write(1,b'\\n')
elif mode=='tail_notification':
    os.write(1,(line+json.dumps({'method':'unexpected/notification','params':{}})+'\\n').encode())
else:
    os.write(1,(line+line if mode in ('duplicate_response','tail_duplicate') else line).encode())
time.sleep(60)
'''
    def launch(arguments, **kwargs):
        options.append((arguments, kwargs))
        child = real_popen([sys.executable, '-I', '-S', '-c', peer, mode], **kwargs)
        children.append(child)
        if mode == 'slow_launch':
            time.sleep(0.4)
        elif mode == 'reap_unverified':
            real_wait = child.wait
            def unverified_wait(*args, **kwargs):
                real_wait(*args, **kwargs)
                raise subprocess.TimeoutExpired('synthetic-unverified-reap', 0)
            monkeypatch.setattr(child, 'wait', unverified_wait)
        return child
    monkeypatch.setattr(module.subprocess, 'Popen', launch)
    monkeypatch.setattr(module, 'WALL_SECONDS', 0.35)
    if mode in {'tail_duplicate', 'tail_notification'}:
        original_read = os.read
        def one_stdout_byte(descriptor, size):
            if children and descriptor == children[-1].stdout.fileno():
                size = 1
            return original_read(descriptor, size)
        monkeypatch.setattr(module.os, 'read', one_stdout_byte)
    elif mode == 'tail_stderr':
        original_selector = module.selectors.DefaultSelector
        class StdoutFirst(original_selector):
            def register(self, fileobj, events, data=None):
                # Model a legal scheduling boundary: response arrives before
                # any stderr readiness is observed. Reaping must still drain it.
                if data != 'stderr':
                    return super().register(fileobj, events, data)
        monkeypatch.setattr(module.selectors, 'DefaultSelector', StdoutFirst)
    descriptor = os.open('/dev/null', os.O_RDONLY)
    try:
        outcome = runtime._observe(descriptor, frozen, 'codex_owner_synthetic')
        assert outcome.status == status
        runtime.validate_outcome(frozen, 'codex_owner_synthetic', outcome)
        assert len(children) == 1 and children[0].poll() is not None
        assert children[0].stdin.closed and children[0].stdout.closed and children[0].stderr.closed
        with pytest.raises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)
        arguments, kwargs = options[0]
        assert arguments[1:5] == ['-I', '-S', '-B', '-c']
        assert 'restrict_probe' in arguments[5] and 'prctl(1, signal.SIGKILL' in arguments[5]
        assert kwargs['start_new_session'] is True and kwargs['close_fds'] is True
        assert kwargs['pass_fds'] == (descriptor,)
        assert len(kwargs['env']) == 9
        if status != 'ready':
            assert outcome.thread_id is outcome.receipt_json is None
    finally:
        os.close(descriptor)
