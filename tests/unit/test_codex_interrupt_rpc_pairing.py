"""Offline local frames are observations, never live transport or shutdown proof."""
from pathlib import Path


def test_local_interrupt_reply_and_terminal_are_separate_exact_observations():
    package = Path(__file__).parents[2] / 'services/api/app/infrastructure/codex_interrupt_protocol'
    assert (package / 'source-summary.json').is_file(), 'Interrupt RPC/event originals are not packaged'

    from services.api.app.infrastructure.codex_interrupt_protocol import (
        observe_interrupt, prepare_interrupt, read_interrupt_source,
    )

    source = read_interrupt_source()
    request = b'{"id":7,"method":"turn/interrupt","params":{"threadId":"thread-fixture","turnId":"turn-fixture"}}'
    exchange = prepare_interrupt(source, request)
    assert exchange.implemented is False
    assert exchange.production_qualification == 'unregistered'
    assert not exchange.control_reply_observed


def test_original_exchange_detects_missing_observation_members():
    from services.api.app.infrastructure.codex_interrupt_protocol import (
        observe_interrupt, prepare_interrupt, read_interrupt_source, verify_interrupt_exchange,
    )
    import pytest

    source = read_interrupt_source()
    exchange = prepare_interrupt(source, b'{"id":7,"method":"turn/interrupt","params":{"threadId":"t","turnId":"u"}}')
    acknowledged = observe_interrupt(source, exchange, b'{"id":7,"result":{}}').exchange
    assert acknowledged.observation_count == 1
    acknowledged.observations.clear()
    with pytest.raises(ValueError):
        verify_interrupt_exchange(source, acknowledged)
    assert not exchange.terminal_notification_observed
    reply = b'{"id":7,"result":{}}'
    acknowledged = observe_interrupt(source, exchange, reply)
    assert acknowledged.accepted is True
    assert acknowledged.exchange.control_reply_observed
    assert not acknowledged.exchange.terminal_notification_observed
    terminal = b'{"method":"turn/completed","params":{"threadId":"thread-fixture","turn":{"id":"turn-fixture","items":[],"status":"interrupted"}}}'
    completed = observe_interrupt(source, acknowledged.exchange, terminal)
    assert completed.accepted is True
    assert completed.exchange.control_reply_observed
    assert completed.exchange.terminal_notification_observed
    assert completed.exchange.observations[0].frame.raw == reply
    assert completed.exchange.observations[1].frame.raw == terminal
    assert exchange.request.frame.raw == request
    assert not exchange.control_reply_observed
