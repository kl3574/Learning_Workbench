"""Selected test-instance metadata only. Never imported by production composition.

All hooks append bounded primitives in memory, without blocking for a lock or IO.
Snapshots are later observations, never witnesses of an earlier browser deadline.
"""
from contextvars import ContextVar
from functools import wraps
import re
import threading
from time import perf_counter_ns
from uuid import uuid4

_CONTEXT = ContextVar('tutor_observation_request', default=None)
_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,79}$')
_CORRELATION = re.compile(r'^[A-Za-z0-9_-]{1,96}:\d{1,16}$')
_EVENTS = {'queued', 'context_ready', 'retrieval_completed', 'answer_delta', 'citation', 'approval_required',
           'usage', 'completed', 'failed', 'cancelled'}
_STAGES = {'run_bound', 'request_entered', 'request_returned', 'request_raised', 'response_started', 'frame_offered',
           'asgi_send_returned', 'owner_read_entered', 'owner_read_returned', 'owner_events_entered',
           'owner_events_returned', 'owner_authorize_returned', 'provider_terminal_commit_returned',
           'consumer_step_returned', 'tutor_terminal_committed'}


class TutorObservation:
    def __init__(self, capacity=1024):
        self.epoch = uuid4().hex
        self._start = perf_counter_ns()
        self._capacity = max(1, min(1024, capacity))
        self._lock = threading.Lock()
        self._records = []
        self._run = None
        self._omitted = self._invalid = 0

    def bind(self, run):
        # Bind only the actual successful first Tutor start of this isolated app.
        if self._run is None and isinstance(run, str) and run.startswith('run_') and _ID.fullmatch(run):
            self._run = run
            self.emit('run_bound', run)

    def emit(self, stage, run, **facts):
        try:
            if self._run is None or run != self._run:
                return
            allowed = {'seq', 'revision', 'after', 'http_status', 'status', 'event', 'request', 'correlation', 'receipt', 'dispatch'}
            valid = stage in _STAGES and not facts.keys() - allowed
            for key, value in facts.items():
                if key in {'seq', 'revision', 'after', 'http_status'}:
                    valid = valid and type(value) is int and 0 <= value <= 2**53 - 1
                elif key == 'status':
                    valid = valid and value in {'queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'}
                elif key == 'event':
                    valid = valid and value in _EVENTS
                elif key == 'correlation':
                    valid = valid and isinstance(value, str) and bool(_CORRELATION.fullmatch(value))
                else:
                    valid = valid and isinstance(value, str) and bool(_ID.fullmatch(value))
            if not valid:
                self._invalid += 1
                return
            if not self._lock.acquire(blocking=False):
                self._omitted += 1
                return
            try:
                if len(self._records) >= self._capacity:
                    self._omitted += 1
                    return
                context = _CONTEXT.get()
                inherited = context[1] if context is not None and context[0] == run else {}
                self._records.append({'epoch': self.epoch, 'ordinal': len(self._records) + 1,
                    'source_ns': perf_counter_ns() - self._start, 'stage': stage, 'run': run, **inherited, **facts})
            finally:
                self._lock.release()
        except Exception:
            self._invalid += 1

    def snapshot(self):
        acquired = self._lock.acquire(blocking=False)
        try:
            return {'epoch': self.epoch, 'selected_run': self._run, 'snapshot_source_ns': perf_counter_ns() - self._start, 'records': [dict(x) for x in self._records] if acquired else [],
                'omitted': self._omitted, 'invalid': self._invalid, 'snapshot_contended': not acquired,
                'clock': 'API perf_counter_ns since recorder construction; no cross-clock alignment'}
        finally:
            if acquired:
                self._lock.release()


def install_owner_observation(service, worker, dispatch, recorder):
    original_start = service.start
    @wraps(original_start)
    def start(*args, **kwargs):
        value = original_start(*args, **kwargs)
        recorder.bind(value.run.id)
        return value
    service.start = start
    for method in ('read', 'events'):
        original = getattr(service, method)
        def wrap(original, method):
            @wraps(original)
            def observed(identity, identifier, *args, **kwargs):
                recorder.emit(f'owner_{method}_entered', identifier)
                value = original(identity, identifier, *args, **kwargs)
                facts = {'seq': value.run.last_seq, 'revision': value.job_revision, 'status': value.run.status} if method == 'read' else {}
                recorder.emit(f'owner_{method}_returned', identifier, **facts)
                return value
            return observed
        setattr(service, method, wrap(original, method))
    original_authorize = service.authorize
    @wraps(original_authorize)
    def authorize(identity, thread_id=None, run_id=None):
        value = original_authorize(identity, thread_id, run_id)
        recorder.emit('owner_authorize_returned', run_id)
        return value
    service.authorize = authorize
    original_consume = worker._consume
    @wraps(original_consume)
    def consume(identity, lease, event):
        value = original_consume(identity, lease, event)
        recorder.emit('consumer_step_returned', lease.job_id)
        return value
    worker._consume = consume
    worker.terminal_observer = lambda run, status: recorder.emit('tutor_terminal_committed', run, status=status)
    if dispatch is not None:
        original_finish = dispatch._finish
        @wraps(original_finish)
        def finish(*args, **kwargs):
            receipt = original_finish(*args, **kwargs)
            recorder.emit('provider_terminal_commit_returned', receipt.job_id, receipt=receipt.id, dispatch=receipt.dispatch_id)
            return receipt
        dispatch._finish = finish


class TutorObservationMiddleware:
    def __init__(self, app, recorder):
        self.app, self.recorder = app, recorder

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        match = re.fullmatch(r'/api/v1/runs/(run_[A-Za-z0-9_-]{1,75})(/events)?', path)
        if scope['type'] != 'http' or scope.get('method') != 'GET' or match is None:
            return await self.app(scope, receive, send)
        run = match[1]
        facts = {'request': 'request_' + uuid4().hex}
        labels = [v for k, v in scope.get('headers', []) if k == b'x-tutor-observation']
        if len(labels) == 1 and len(labels[0]) <= 113:
            label = labels[0].decode('ascii', errors='replace')
            if _CORRELATION.fullmatch(label):
                facts['correlation'] = label
        cursor = re.fullmatch(rb'after_seq=(\d{1,16})', scope.get('query_string', b''))
        if cursor and int(cursor[1]) <= 2**53 - 1:
            facts['after'] = int(cursor[1])
        context = _CONTEXT.set((run, facts))
        self.recorder.emit('request_entered', run)
        async def observed_send(message):
            if message['type'] == 'http.response.start':
                self.recorder.emit('response_started', run, http_status=message['status'])
            frame = None
            if match[2] and message['type'] == 'http.response.body':
                # Inspect only the bounded id/event prefix; never decode/retain data.
                body = message.get('body', b'')
                first = body.find(b'\n', 0, 240)
                second = body.find(b'\n', first + 1, 240) if first >= 0 else -1
                prefix = body[:second + 1] if second >= 0 else b''
                frame = re.match(rb'id: ([A-Za-z][A-Za-z0-9_-]{0,79}):(\d{1,16})\nevent: ([a-z_]{1,32})\n', prefix)
                if frame and frame[1].decode() == run and frame[3].decode() in _EVENTS:
                    self.recorder.emit('frame_offered', run, seq=int(frame[2]), event=frame[3].decode())
                else:
                    frame = None
            await send(message)
            if frame:
                self.recorder.emit('asgi_send_returned', run, seq=int(frame[2]), event=frame[3].decode())
        try:
            value = await self.app(scope, receive, observed_send)
            self.recorder.emit('request_returned', run)
            return value
        except BaseException:
            self.recorder.emit('request_raised', run)
            raise
        finally:
            _CONTEXT.reset(context)
