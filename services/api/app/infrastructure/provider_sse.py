"""Bounded SSE decoding, cumulative usage and one checked terminal per stream."""
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, cast
import codecs
import asyncio
import re

from packages.contracts.canonical import strict_json
from ..application.provider_models import (
    CheckedProviderDelta, CheckedProviderError, CheckedProviderEvent, CheckedProviderFinished,
    CheckedProviderUsage, UsageSnapshot,
)
from ..provider_dto import ProviderFailureCode


T = TypeVar('T')


async def parser_work(operation: Callable[[], T]) -> T:
    worker = asyncio.create_task(asyncio.to_thread(operation))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        # A parser invocation owns mutable stream state. Join the bounded work
        # before cancellation cleanup inspects its final accepted state.
        await asyncio.gather(worker, return_exceptions=True)
        raise


class ProtocolFailure(Exception):
    def __init__(self, code: ProviderFailureCode = 'PROVIDER_PROTOCOL_ERROR'):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SSEFrame:
    event: str | None
    data: str


class SSEDecoder:
    def __init__(self) -> None:
        self.decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        self.line_parts: list[str] = []
        self.line_length = 0
        self.data: list[str] = []
        self.event: str | None = None
        self.pending_cr = False
        self.total = self.frame_size = 0

    def feed(self, chunk: bytes) -> list[SSEFrame]:
        self.total += len(chunk)
        if self.total > 8 * 1024 * 1024:
            raise ProtocolFailure()
        try:
            text = self.decoder.decode(chunk)
        except UnicodeError:
            raise ProtocolFailure() from None
        result = []
        if self.pending_cr:
            self.pending_cr = False
            if text.startswith('\n'):
                text = text[1:]
        offset = 0
        for separator in re.finditer(r'\r\n|\r|\n', text):
            part = text[offset:separator.start()]
            self.line_parts.append(part)
            self.line_length += len(part)
            if self.line_length > 256 * 1024:
                raise ProtocolFailure()
            line = ''.join(self.line_parts)
            self.line_parts, self.line_length = [], 0
            if not line:
                if self.data:
                    result.append(SSEFrame(self.event, '\n'.join(self.data)))
                self.data, self.event, self.frame_size = [], None, 0
            elif not line.startswith(':'):
                key, exists, value = line.partition(':')
                if exists and value.startswith(' '):
                    value = value[1:]
                if key == 'data':
                    self.data.append(value)
                    self.frame_size += len(value)
                    if self.frame_size > 1024 * 1024:
                        raise ProtocolFailure()
                elif key == 'event':
                    if self.event is not None:
                        raise ProtocolFailure()
                    self.event = value
                elif key not in {'id', 'retry'}:
                    raise ProtocolFailure()
            offset = separator.end()
            self.pending_cr = separator.group() == '\r' and offset == len(text)
        remainder = text[offset:]
        if remainder:
            self.line_parts.append(remainder)
            self.line_length += len(remainder)
            if self.line_length > 256 * 1024:
                raise ProtocolFailure()

        return result

    def eof(self) -> None:
        try:
            self.decoder.decode(b'', final=True)
        except UnicodeError:
            raise ProtocolFailure() from None
        # Unterminated records are never fabricated into complete SSE events.


async def frames(chunks: AsyncIterator[bytes]) -> AsyncIterator[SSEFrame]:
    decoder = SSEDecoder()
    async for chunk in chunks:
        for frame in decoder.feed(chunk):
            yield frame
    decoder.eof()


def object_data(frame: SSEFrame) -> dict[str, Any]:
    try:
        value = strict_json(frame.data)
    except (ValueError, TypeError):
        raise ProtocolFailure() from None
    if not isinstance(value, dict):
        raise ProtocolFailure()
    return value


class ProtocolState:
    def __init__(self) -> None:
        self.usage = UsageSnapshot(input_tokens=None, output_tokens=None)
        self.answer_parts: list[str] = []
        self.refusal_parts: list[str] = []
        self.output_bytes = 0
        self.provider_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown'] = 'unknown'
        self.terminal = False

    @property
    def answer(self) -> str:
        return ''.join(self.answer_parts)

    @property
    def refusal(self) -> str:
        return ''.join(self.refusal_parts)

    def delta(self, channel: Literal['answer', 'refusal'], value: object) -> list[CheckedProviderEvent]:
        if value is None or value == '':
            return []
        if not isinstance(value, str):
            raise ProtocolFailure()
        size = len(value.encode())
        if self.output_bytes + size > 4 * 1024 * 1024:
            raise ProtocolFailure()
        self.output_bytes += size
        (self.answer_parts if channel == 'answer' else self.refusal_parts).append(value)
        return [CheckedProviderDelta(type='delta', channel=channel, text=value)]

    def accept_usage(self, value: object, *, chat: bool = False) -> list[CheckedProviderEvent]:
        if value is None:
            return []
        if not isinstance(value, dict):
            raise ProtocolFailure('PROVIDER_USAGE_INCONSISTENT')
        names = ('prompt_tokens', 'completion_tokens') if chat else ('input_tokens', 'output_tokens')
        old = (self.usage.input_tokens, self.usage.output_tokens)
        counts: list[int | None] = []
        for name, previous in zip(names, old, strict=True):
            count = value.get(name)
            if count is None:
                counts.append(previous)
            elif type(count) is not int or count < 0 or (previous is not None and count < previous):
                raise ProtocolFailure('PROVIDER_USAGE_INCONSISTENT')
            else:
                counts.append(count)
        total = value.get('total_tokens')
        if total is not None and (type(total) is not int or total < 0
                or (all(v is not None for v in counts) and total != sum(v for v in counts if v is not None))):
            raise ProtocolFailure('PROVIDER_USAGE_INCONSISTENT')
        new = UsageSnapshot(input_tokens=counts[0], output_tokens=counts[1])
        if new == self.usage:
            return []
        self.usage = new
        return [CheckedProviderUsage(type='usage', **new.model_dump())]

    def finish(self, outcome: Literal['complete', 'refused', 'incomplete'],
               reason: Literal['output_limit', 'content_filter', 'provider_incomplete'] | None = None
               ) -> CheckedProviderFinished:
        self.terminal = True
        if outcome == 'complete' and self.refusal_parts:
            outcome = 'refused'
        return CheckedProviderFinished(type='finished', outcome=outcome, reason=reason,
            output_state=('partial' if outcome == 'incomplete' else 'complete') if self.output_bytes else 'none',
            usage=self.usage)

    def error(self, code: ProviderFailureCode) -> CheckedProviderError:
        self.terminal = True
        return CheckedProviderError(type='error', error_code=code, provider_outcome=self.provider_outcome,
            output_state='partial' if self.output_bytes else 'none', usage=self.usage)


class ProtocolDecoder:
    def __init__(self, adapter: str, model: str):
        from .provider_compatible_chat import ChatParser
        from .provider_responses import ResponsesParser
        if adapter not in {'compatible_chat', 'official_responses'}:
            raise ProtocolFailure()
        self.state = ChatParser(model) if adapter == 'compatible_chat' else ResponsesParser(model)

    async def stream(self, chunks: AsyncIterator[bytes]) -> AsyncGenerator[CheckedProviderEvent, None]:
        framing = SSEDecoder()
        sent_answer = sent_refusal = 0
        try:
            async for chunk in chunks:
                terminal: CheckedProviderFinished | CheckedProviderError | None = None
                # Decode all complete records in bytes already delivered by HTTP.
                # Hold the terminal until that received batch is checked; do not
                # fetch another network chunk merely to predict future events.
                for frame in await parser_work(lambda: framing.feed(chunk)):
                    if terminal is not None:
                        raise ProtocolFailure()
                    for event in await parser_work(lambda: self.state.feed(frame)):
                        if event.type in {'finished', 'error'}:
                            terminal = event
                        else:
                            if event.type == 'delta':
                                if event.channel == 'answer':
                                    sent_answer += len(event.text)
                                else:
                                    sent_refusal += len(event.text)
                            yield event
                if terminal is not None:
                    yield terminal
                    return
            framing.eof()
        except (ProtocolFailure, ValueError, TypeError, KeyError, IndexError) as exc:
            # A frame may contain valid text followed by invalid usage metadata.
            # Preserve text already accepted by the channel parser, even when
            # its enclosing feed could not return the usual event list.
            for channel, text in [('answer', self.state.answer[sent_answer:]),
                                  ('refusal', self.state.refusal[sent_refusal:])]:
                if text:
                    yield CheckedProviderDelta(type='delta', channel=cast(Literal['answer', 'refusal'], channel), text=text)
            yield self.state.error(exc.code if isinstance(exc, ProtocolFailure) else 'PROVIDER_PROTOCOL_ERROR')
            return
        yield self.state.error('PROVIDER_OUTCOME_UNKNOWN')


async def checked_stream(chunks: AsyncIterator[bytes], adapter: str, model: str) -> AsyncGenerator[CheckedProviderEvent, None]:
    async for event in ProtocolDecoder(adapter, model).stream(chunks):
        yield event
