"""Qualified single-choice text Chat Completions SSE protocol."""
from ..application.provider_models import CheckedProviderEvent
from .provider_sse import ProtocolFailure, ProtocolState, SSEFrame, object_data


class ChatParser(ProtocolState):
    def __init__(self, model: str):
        super().__init__()
        self.model = model
        self.identifier: str | None = None
        self.finish_reason: str | None = None

    def feed(self, frame: SSEFrame) -> list[CheckedProviderEvent]:
        if self.terminal:
            raise ProtocolFailure()
        if frame.event not in {None, 'message'}:
            raise ProtocolFailure()
        if frame.data == '[DONE]':
            if self.finish_reason is None:
                raise ProtocolFailure()
            if self.finish_reason == 'stop':
                return [self.finish('complete')]
            return [self.finish('incomplete', 'output_limit' if self.finish_reason == 'length' else 'content_filter')]
        value = object_data(frame)
        if 'error' in value:
            self.provider_outcome = 'failed'
            return [self.error('PROVIDER_TRANSPORT_ERROR')]
        identifier = value.get('id')
        if (not isinstance(identifier, str) or not identifier or value.get('model') != self.model
                or (self.identifier is not None and identifier != self.identifier)
                or value.get('object', 'chat.completion.chunk') != 'chat.completion.chunk'):
            raise ProtocolFailure()
        self.identifier = identifier
        choices = value.get('choices')
        if not isinstance(choices, list) or len(choices) > 1:
            raise ProtocolFailure()
        result: list[CheckedProviderEvent] = []
        if choices:
            item = choices[0]
            if not isinstance(item, dict) or type(item.get('index')) is not int or item['index'] != 0:
                raise ProtocolFailure()
            delta = item.get('delta')
            if not isinstance(delta, dict) or set(delta) - {'role', 'content', 'refusal'}:
                raise ProtocolFailure()
            if delta.get('role') not in {None, 'assistant'}:
                raise ProtocolFailure()
            if self.finish_reason is not None:
                raise ProtocolFailure()
            result += self.delta('answer', delta.get('content'))
            result += self.delta('refusal', delta.get('refusal'))
            finish = item.get('finish_reason')
            if finish is not None:
                if finish not in {'stop', 'length', 'content_filter'}:
                    raise ProtocolFailure()
                self.finish_reason = finish
                self.provider_outcome = 'completed' if finish == 'stop' else 'incomplete'
        elif value.get('usage') is None:
            raise ProtocolFailure()
        result += self.accept_usage(value.get('usage'), chat=True)
        return result
