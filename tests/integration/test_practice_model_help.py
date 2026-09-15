"""Practice assistance from real local Tutor/Provider output, never a paid model.

The loopback proof is an explicit synthetic protocol premise. It does not assert
production model availability, answer correctness or browser delivery.
"""
import asyncio

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json
from services.api.app.application.content import ContentService
from services.api.app.application.practice import PracticeService
from services.api.app.application.tutor import TutorService
from services.api.app.application.tutor_context import ContextService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.practice_dto import PracticeSessionCreate, PracticeSubmitRequest
from services.api.app.tutor_dto import TutorContextBinding, TutorPracticeBinding, TutorRunCancel, TutorThreadCreate
from tests.integration.test_tutor_runs import approved, configured
from tests.practice_fixtures import practice_fixture
from tests.provider_protocol_fixture import chat_stream, local_provider


def setup_practice(tmp_path, *, submitted=False):
    db = Database(Settings(data_dir=tmp_path / 'data'))
    ws = db.initialize()
    identity = SessionIdentity('session_model_help', ws, 'learner', 'unused', '2099-01-01T00:00:00Z')
    fixture = practice_fixture('modelhelp')
    ContentService(db).publish(ws, fixture.public_objects, fixture.bodies)
    practice = PracticeService(db)
    session = practice.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'create')
    original_submit = None
    if submitted:
        original_submit = practice.submit(identity, session.id, PracticeSubmitRequest(expected_revision=session.revision), 'submit')
        session = practice.get_session(identity, session.id)
    binding = TutorContextBinding(practice=TutorPracticeBinding(session_id=session.id,
        session_revision=session.revision, question_ref=reference(fixture.questions[0])), assessment=None)
    create = TutorThreadCreate(scope=dm.ViewContext(view_kind='practice', active_ref=reference(fixture.practice)),
        binding=binding, title='真实模型帮助记录')
    tutor = (db, identity, TutorService(db, ContextService(db)), create)
    return tutor, practice, session, original_submit


@pytest.mark.parametrize('submitted_before', [False, True])
def test_model_answer_marks_current_assisted_without_rewriting_original_submission(tmp_path, submitted_before):
    tutor, practice, original, old_submit = setup_practice(tmp_path, submitted=submitted_before)
    db, identity, service, _ = tutor
    async def run():
        async with local_provider(text='先识别题目中的两个加数，再尝试计算。\n') as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, _, run, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            with db.connect() as conn:
                raw_before = tuple(conn.execute('SELECT revision,submission_json,submission_sha256 FROM practice_sessions WHERE id=?', (original.id,)).fetchone())
            assert not practice.get_session(identity, original.id).assisted
            assert await asyncio.to_thread(worker.run_once)
            assert service.read(identity, run.run.id).run.status == 'completed'
            current = practice.get_session(identity, original.id)
            assert current.assisted, 'actual model output must not remain unassisted'
            assert current.revision == original.revision
            assert current.assistance[0].model_help_received
            assert current.assistance[0].highest_hint_level == 0
            assert not current.assistance[0].solution_revealed
            assert all(not item.model_help_received for item in current.assistance[1:])
            assert len(current.exposure_event_ids) == 1
            with db.connect() as conn:
                assert tuple(conn.execute('SELECT revision,submission_json,submission_sha256 FROM practice_sessions WHERE id=?', (original.id,)).fetchone()) == raw_before
                assert conn.execute('SELECT COUNT(*) FROM practice_exposures').fetchone()[0] == 0
            if submitted_before:
                assert old_submit is not None and not old_submit.assisted
                assert practice.submit(identity, original.id, PracticeSubmitRequest(expected_revision=1), 'submit') == old_submit
            else:
                result = practice.submit(identity, original.id, PracticeSubmitRequest(expected_revision=original.revision), 'submit')
                assert result.assisted and result.assistance[0].model_help_received
                assert result.exposure_event_ids == current.exposure_event_ids
            assert not await asyncio.to_thread(worker.run_once) and len(server.requests) == 1
    asyncio.run(run())


def test_refusal_only_keeps_practice_unassisted(tmp_path):
    tutor, practice, session, _ = setup_practice(tmp_path)
    _, identity, service, _ = tutor
    async def run():
        async with local_provider(payload=chat_stream('无法回答。', refusal=True)) as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            assert await asyncio.to_thread(worker.run_once)
            assert service.read(identity, original.run.id).result.refusal_markdown == '无法回答。'
            current = practice.get_session(identity, session.id)
            assert not current.assisted and not current.exposure_event_ids
    asyncio.run(run())


def split_stream():
    # Real protocol frames: preserve whitespace and two distinct answer deltas.
    frames = chat_stream('先辨认加数。\n').split(b'\n\n')
    delta = strict_json(frames[1][6:])
    delta['choices'][0]['delta']['content'] = '再尝试计算。'
    return b'\n\n'.join([frames[0], b'data: ' + canonical_bytes({**delta,
        'choices': [{'index': 0, 'delta': {'content': ' \n'}, 'finish_reason': None}]}),
        frames[1], b'data: ' + canonical_bytes(delta), *frames[2:]])


@pytest.mark.parametrize('mode', ['normal', 'cancel_after_delta', 'restore_terminal_without_deltas'])
def test_multiple_deltas_cancel_and_terminal_recovery_keep_one_original_help(tmp_path, monkeypatch, mode):
    from services.api.app.application.practice_help_access import help_witnesses, validate_help_witnesses
    from services.api.app.application.practice_history import PracticeHistory
    from services.api.app.application.tutor_models import PreparedTutorContext
    from services.api.app.infrastructure.practice_model_help_repository import PracticeModelHelpRepository
    from services.api.app.infrastructure.practice_repository import PracticeRepository
    from services.api.app.application.practice_content import PracticeContent
    tutor, practice, session, _ = setup_practice(tmp_path)
    db, identity, service, create = tutor
    async def run():
        async with local_provider(payload=split_stream()) as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            frozen: PreparedTutorContext
            with db.transaction(immediate=False) as conn:
                context_id = service.read(identity, original.run.id).run.context_snapshot_id
                frozen = service.context.read(conn, identity, context_id)
            consume = worker._consume
            cancelled = False
            def observe(identity_, lease, event):
                nonlocal cancelled
                if mode == 'restore_terminal_without_deltas' and event.type == 'delta':
                    return  # Controlled consumer-loss seam; Provider retains the real artifact.
                consume(identity_, lease, event)
                if event.type == 'delta' and event.channel == 'answer' and event.text.strip():
                    with db.transaction(immediate=False) as conn:
                        service.context.verify(conn, identity, frozen)
                    if mode == 'cancel_after_delta' and not cancelled:
                        current = service.read(identity, original.run.id)
                        service.cancel(identity, original.run.id, TutorRunCancel(expected_revision=current.job_revision), 'cancel')
                        cancelled = True
            monkeypatch.setattr(worker, '_consume', observe)
            assert await asyncio.to_thread(worker.run_once)
            result = service.read(identity, original.run.id)
            assert result.run.status == ('cancelled' if mode == 'cancel_after_delta' else 'completed')
            view = practice.get_session(identity, session.id)
            assert view.assisted and view.revision == session.revision
            assert len(view.exposure_event_ids) == 1 and view.assistance[0].model_help_received
            with db.transaction(immediate=False) as conn:
                records = PracticeModelHelpRepository(conn, identity.workspace_id)
                receipt = records.read(original.run.id)
                assert receipt is not None and receipt.event_id == view.exposure_event_ids[0]
                events = service.events(identity, original.run.id, 0)
                first = next(e for e in events if e.type == 'answer_delta' and e.text.strip())
                assert receipt.answer.event_seq == first.seq
                assert receipt.source == 'model'
                session_record = PracticeRepository(conn, identity.workspace_id).load(session.id)
                questions = PracticeContent(conn, identity.workspace_id).questions(PracticeContent(conn, identity.workspace_id).practice(session_record.practice_ref))
                seen = PracticeHistory(conn, identity.workspace_id).seen(questions)
                assert all(item.state == 'seen' for item in seen)
                facts = help_witnesses(conn, identity.workspace_id, create.binding.practice.question_ref,
                    questions[0].exposure_group, '2000-01-01T00:00:00Z', '2099-01-01T00:00:00Z')
                assert facts.pre_submission_state == facts.in_attempt_state == 'present'
                assert len(facts.witnesses) == 1 and facts.witnesses[0].level == 0
                validate_help_witnesses(conn, identity.workspace_id, facts.witnesses)
            assert len(server.requests) == 1 and not await asyncio.to_thread(worker.run_once)
            if mode == 'normal':
                assert result.run.answer_markdown == ' \n先辨认加数。\n再尝试计算。'
                practice.save_responses(identity, session.id, dm.ResponsesWrite(expected_revision=session.revision,
                    responses=[dm.ResponseDraft(question_id=create.binding.practice.question_ref.id, answer='choice_five')]), 'save')
                from services.api.app.application.errors import ApiError
                with db.transaction(immediate=False) as conn, pytest.raises(ApiError) as changed:
                    service.context.verify(conn, identity, frozen)
                assert changed.value.code == 'TUTOR_CONTEXT_CHANGED'
    asyncio.run(run())


def test_failed_help_write_rolls_back_tutor_delta_and_all_exposure_rows(tmp_path, monkeypatch):
    from services.api.app.infrastructure.practice_model_help_repository import PracticeModelHelpRepository
    tutor, practice, session, _ = setup_practice(tmp_path)
    db, identity, service, _ = tutor
    class AbortTransaction(Exception):
        pass
    insert = PracticeModelHelpRepository.insert
    def abort(repository, receipt):
        insert(repository, receipt)
        raise AbortTransaction()
    async def run():
        async with local_provider(text='真实已收到的帮助。') as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            monkeypatch.setattr(PracticeModelHelpRepository, 'insert', abort)
            with pytest.raises(AbortTransaction):
                await asyncio.to_thread(worker.run_once)
            assert service.read(identity, original.run.id).run.answer_markdown == ''
            assert not practice.get_session(identity, session.id).assisted
            with db.connect() as conn:
                assert conn.execute('SELECT COUNT(*) FROM practice_model_help').fetchone()[0] == 0
                assert conn.execute('SELECT COUNT(*) FROM exposures').fetchone()[0] == 0
                assert conn.execute("SELECT COUNT(*) FROM learning_events WHERE kind='hint_revealed'").fetchone()[0] == 0
    asyncio.run(run())


@pytest.mark.parametrize('fault', ['missing_receipt', 'wrong_event_seq', 'wrong_text_sha'])
def test_model_help_corruption_fails_closed_even_with_recomputed_receipt_hash(tmp_path, fault):
    from services.api.app.application.errors import ApiError
    from packages.contracts.canonical import sha256_bytes
    tutor, practice, session, _ = setup_practice(tmp_path)
    db, identity, _, _ = tutor
    async def run():
        async with local_provider(text='真实原始模型帮助。') as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, _, original, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            assert await asyncio.to_thread(worker.run_once)
            assert practice.get_session(identity, session.id).assisted
            # Explicit tamper fixture, not an application mutation path.
            with db.transaction() as conn:
                if fault == 'missing_receipt':
                    conn.execute('DROP TRIGGER practice_model_help_no_delete')
                    conn.execute('DELETE FROM practice_model_help WHERE run_id=?', (original.run.id,))
                else:
                    conn.execute('DROP TRIGGER practice_model_help_no_update')
                    raw = conn.execute('SELECT receipt_json FROM practice_model_help WHERE run_id=?', (original.run.id,)).fetchone()[0]
                    value = strict_json(raw)
                    if fault == 'wrong_event_seq':
                        value['answer']['event_seq'] += 1
                    else:
                        value['answer']['text_sha256'] = '0' * 64
                    payload = canonical_bytes(value)
                    conn.execute('UPDATE practice_model_help SET receipt_json=?,receipt_sha256=? WHERE run_id=?',
                        (payload.decode(), sha256_bytes(payload), original.run.id))
            with pytest.raises(ApiError) as invalid:
                practice.get_session(identity, session.id)
            assert invalid.value.code == 'PRACTICE_SNAPSHOT_INVALID'
    asyncio.run(run())


def test_legacy_assistance_storage_and_strict_public_boolean_stay_separate():
    from pydantic import ValidationError
    from services.api.app.practice_dto import PracticeAssistance, PracticeAssistanceView
    legacy = {'question_id': 'question_legacy', 'highest_hint_level': 0, 'solution_revealed': False}
    assert PracticeAssistance.model_validate(legacy).model_dump() == legacy
    assert PracticeAssistanceView.model_validate(legacy).model_help_received is False
    for wrong in (None, 0, 1, 'true'):
        with pytest.raises(ValidationError):
            PracticeAssistanceView.model_validate({**legacy, 'model_help_received': wrong})
