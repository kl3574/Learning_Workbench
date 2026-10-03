"""Control only a real parent scheduling gap; never replace parser/HTTP/pipe values."""
import json
import os
import threading
import time
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def real_parser_poll_exit_gap(monkeypatch, request):
    if request.node.name != 'test_failed_documents_report_safe_failure_and_retain_exact_original_without_formal_content[pdf-pdf_scan_fixture-True]':
        yield
        return
    from services.api.app.infrastructure.import_worker import _parse_process
    original_start, original_poll, original_recv = BaseProcess.start, Connection.poll, Connection.recv
    processes=[]
    gated=False
    output=Path(os.environ['LW_PDF_DIAG_FILE'])
    def record(**event):
        event['monotonic_ns']=time.monotonic_ns()
        with output.open('a') as target:target.write(json.dumps(event,sort_keys=True)+'\n')
    def start(process,*args,**kwargs):
        selected=getattr(process,'_target',None) is _parse_process
        value=original_start(process,*args,**kwargs)
        if selected:
            processes.append(process)
            record(event='actual_parser_started',pid=process.pid,parent_pid=os.getpid())
        return value
    def poll(connection,timeout=0.0):
        nonlocal gated
        value=original_poll(connection,timeout)
        if (not gated and not value and timeout==0.1 and processes
                and threading.current_thread().name=='learning-import-worker'):
            gated=True
            process=processes[-1]
            record(event='actual_poll_returned_false',pid=process.pid)
            # Simulate descheduling after the actual wait result was computed.
            # No result is injected; let this same real parser naturally finish.
            process.join(timeout=5)
            ready=original_poll(connection,0)
            record(event='resume_after_actual_parser_exit',pid=process.pid,
                   exitcode=process.exitcode,alive=process.is_alive(),pipe_ready_now=ready,
                   original_poll_result=value)
        return value
    def recv(connection):
        value=original_recv(connection)
        if threading.current_thread().name=='learning-import-worker':
            kind,payload=value
            code=payload.get('code') if isinstance(payload,dict) else payload if kind=='error' else None
            record(event='actual_parent_recv',kind=kind,code=code)
        return value
    monkeypatch.setattr(BaseProcess,'start',start)
    monkeypatch.setattr(Connection,'poll',poll)
    monkeypatch.setattr(Connection,'recv',recv)
    yield
    record(event='fixture_end',gate_used=gated)
