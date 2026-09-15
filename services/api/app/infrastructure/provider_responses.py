"""Responses parser for the registered text-only, single-message input profile."""
from typing import Any

from ..application.provider_models import CheckedProviderEvent
from .provider_sse import ProtocolFailure, ProtocolState, SSEFrame, object_data


class ResponsesParser(ProtocolState):
    def __init__(self, model: str):
        super().__init__()
        self.model = model
        self.identifier: str | None = None
        self.sequence = -1
        self.item_id: str | None = None
        self.parts: dict[int, tuple[str, list[str], bool]] = {}
        self.item_done = False

    def _part(self, value: dict[str, Any]) -> tuple[int, tuple[str, list[str], bool]]:
        index = value.get('content_index')
        if (value.get('item_id') != self.item_id or type(value.get('output_index')) is not int
                or value['output_index'] != 0 or type(index) is not int or index not in self.parts):
            raise ProtocolFailure()
        return index, self.parts[index]

    def feed(self, frame: SSEFrame) -> list[CheckedProviderEvent]:
        if self.terminal:
            raise ProtocolFailure()
        value = object_data(frame)
        kind = value.get('type')
        if not isinstance(kind, str) or frame.event not in {None, kind}:
            raise ProtocolFailure()
        sequence = value.get('sequence_number')
        if type(sequence) is not int or sequence != self.sequence + 1:
            raise ProtocolFailure()
        self.sequence = sequence
        if kind == 'error':
            self.provider_outcome = 'failed'
            return [self.error('PROVIDER_TRANSPORT_ERROR')]
        response = value.get('response')
        if kind == 'response.created':
            if (self.identifier is not None or not isinstance(response, dict)
                    or not isinstance(response.get('id'), str) or not response['id']
                    or response.get('model') != self.model):
                raise ProtocolFailure()
            self.identifier = response['id']
            return []
        if self.identifier is None:
            raise ProtocolFailure()
        if isinstance(response, dict) and (response.get('id') != self.identifier or response.get('model') != self.model):
            raise ProtocolFailure()
        if kind == 'response.in_progress':
            if not isinstance(response, dict):
                raise ProtocolFailure()
            return []
        if kind == 'response.output_item.added':
            item = value.get('item')
            if (self.item_id is not None or (type(value.get('output_index')) is not int or value.get('output_index') != 0) or not isinstance(item, dict)
                    or item.get('type') != 'message' or item.get('role') != 'assistant'
                    or not isinstance(item.get('id'), str) or not item['id'] or item.get('content') != []):
                raise ProtocolFailure()
            self.item_id = item['id']
            return []
        if kind == 'response.content_part.added':
            index, part = value.get('content_index'), value.get('part')
            if (self.item_done or self.item_id is None or value.get('item_id') != self.item_id
                    or (type(value.get('output_index')) is not int or value.get('output_index') != 0) or type(index) is not int or index != len(self.parts)
                    or not isinstance(part, dict) or part.get('type') not in {'output_text', 'refusal'}):
                raise ProtocolFailure()
            channel = 'answer' if part['type'] == 'output_text' else 'refusal'
            if part.get('text' if channel == 'answer' else 'refusal', '') != '' or part.get('annotations', []) != []:
                raise ProtocolFailure()
            self.parts[index] = (channel, [], False)
            return []
        if kind in {'response.output_text.delta', 'response.refusal.delta'}:
            index, (channel, text, done) = self._part(value)
            if done or self.item_done or channel != ('answer' if kind == 'response.output_text.delta' else 'refusal'):
                raise ProtocolFailure()
            delta = value.get('delta')
            if not isinstance(delta, str):
                raise ProtocolFailure()
            text.append(delta)
            self.parts[index] = (channel, text, False)
            return self.delta('answer' if channel == 'answer' else 'refusal', delta)
        if kind in {'response.output_text.done', 'response.refusal.done'}:
            index, (channel, text, done) = self._part(value)
            if (done or channel != ('answer' if kind == 'response.output_text.done' else 'refusal')
                    or value.get('text' if channel == 'answer' else 'refusal') != ''.join(text)):
                raise ProtocolFailure()
            self.parts[index] = (channel, text, True)
            return []
        if kind == 'response.content_part.done':
            _, (channel, text, done) = self._part(value)
            part = value.get('part')
            if (not done or not isinstance(part, dict)
                    or part.get('type') != ('output_text' if channel == 'answer' else 'refusal')
                    or part.get('text' if channel == 'answer' else 'refusal') != ''.join(text)
                    or part.get('annotations', []) != []):
                raise ProtocolFailure()
            return []
        if kind == 'response.output_item.done':
            item = value.get('item')
            if (self.item_done or (type(value.get('output_index')) is not int or value.get('output_index') != 0) or not isinstance(item, dict)
                    or item.get('id') != self.item_id or item.get('type') != 'message'
                    or item.get('role') != 'assistant'):
                raise ProtocolFailure()
            self._content(item.get('content'))
            self.item_done = True
            return []
        if kind in {'response.completed', 'response.incomplete', 'response.failed'}:
            if not isinstance(response, dict):
                raise ProtocolFailure()
            status = {'response.completed': 'completed', 'response.incomplete': 'incomplete', 'response.failed': 'failed'}[kind]
            if response.get('status') != status:
                raise ProtocolFailure()
            self.provider_outcome = 'completed' if status == 'completed' else ('incomplete' if status == 'incomplete' else 'failed')
            events = self.accept_usage(response.get('usage'))
            if status == 'failed':
                return events + [self.error('PROVIDER_TRANSPORT_ERROR')]
            output = response.get('output')
            if not isinstance(output, list) or len(output) != (1 if self.item_id else 0):
                raise ProtocolFailure()
            if output:
                item = output[0]
                if (not isinstance(item, dict) or item.get('id') != self.item_id
                        or item.get('type') != 'message' or item.get('role') != 'assistant'):
                    raise ProtocolFailure()
                self._content(item.get('content'), require_done=status == 'completed')
            if status == 'completed':
                if self.item_id and not self.item_done:
                    raise ProtocolFailure()
                return events + [self.finish('complete')]
            details = response.get('incomplete_details')
            reason = details.get('reason') if isinstance(details, dict) else None
            if reason not in {'max_output_tokens', 'content_filter', None}:
                raise ProtocolFailure()
            return events + [self.finish('incomplete', 'output_limit' if reason == 'max_output_tokens'
                else 'content_filter' if reason == 'content_filter' else 'provider_incomplete')]
        raise ProtocolFailure()

    def _content(self, content: object, *, require_done: bool = True) -> None:
        if not isinstance(content, list) or len(content) != len(self.parts):
            raise ProtocolFailure()
        for index, part in enumerate(content):
            channel, text, done = self.parts[index]
            if (not isinstance(part, dict) or (require_done and not done)
                    or part.get('type') != ('output_text' if channel == 'answer' else 'refusal')
                    or part.get('text' if channel == 'answer' else 'refusal') != ''.join(text)
                    or part.get('annotations', []) != []):
                raise ProtocolFailure()
