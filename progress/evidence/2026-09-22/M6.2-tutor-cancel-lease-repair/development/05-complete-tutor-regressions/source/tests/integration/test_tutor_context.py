"""Real Tutor/Context/Content owners; synthetic material, no remote transport."""
import hashlib
import json

import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.tutor import TutorService
from services.api.app.application.tutor_context import ContextService, wrapped_size
from services.api.app.application.tutor_source import build_outbound
from services.api.app.application.tutor_worker import TutorWorker
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.tutor_dto import TutorContextBinding, TutorRunCreate, TutorThreadCreate
from tests.integration.test_retrieval import publish_small
from tests.integration.test_tutor_runs import NoTransport


def setup(tmp_path, texts):
    db = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = db.initialize()
    identity = SessionIdentity('context_fixture', workspace, 'learner', '', '2099-01-01T00:00:00Z')
    blocks, lesson, _ = publish_small(db, identity, 'context_boundary', texts)
    service = TutorService(db, ContextService(db))
    return db, identity, blocks, lesson, service


def prepare(values, scope):
    db, identity, _, _, service = values
    binding = TutorContextBinding(practice=None, assessment=None)
    thread = service.create_thread(identity, TutorThreadCreate(scope=scope, binding=binding, title='原创上下文边界'), 'thread')
    ack = service.start(identity, TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id,
        workspace_id=identity.workspace_id, message='请说明当前材料的条件。', intent='derive', context=scope),
        expected_thread_revision=thread.revision, binding=binding), 'run')
    provider = NoTransport()
    worker = TutorWorker(db, service.context, provider, build_outbound)
    assert worker.run_once()
    assert provider.calls == 0
    return service.read(identity, ack.run.id)


def test_current_block_is_exact_and_unicode_selection_does_not_expand_parent(tmp_path):
    text = '前提：x > 0。\n😀在此前提下给出结论。\n'
    values = setup(tmp_path, [text, '未附加的第二块不应发送。'])
    db, identity, blocks, _, service = values
    start = text.index('😀')
    scope = dm.ViewContext(view_kind='lesson', active_ref=reference(blocks[0]), selection=dm.Selection(
        ref=reference(blocks[0]), exact_quote='😀在此', prefix='\n', suffix='前提', start_codepoint=start, end_codepoint=start + 3))
    run = prepare(values, scope)
    assert run.run.status == 'awaiting_approval'
    assert run.context is not None
    assert [item.reference.ref for item in run.context.included] == [reference(blocks[0])]
    assert run.context.included[0].body_sha256 == hashlib.sha256(text.encode()).hexdigest()
    with db.transaction(immediate=False) as conn:
        context = service.context.read(conn, identity, run.context.snapshot.id)
        assert context.evidence[0].text == text
        assert context.snapshot.character_count == sum(len(x.content) for x in context.messages) + sum(map(wrapped_size, context.evidence))
        service.context.verify(conn, identity, context)


@pytest.mark.parametrize('fault', ['outside_scope', 'wrong_quote'])
def test_bad_selection_fails_local_job_without_substituting_similar_text(tmp_path, fault):
    values = setup(tmp_path, ['原始正文。', '另一个正文。'])
    _, _, blocks, _, _ = values
    ref = reference(blocks[1 if fault == 'outside_scope' else 0])
    scope = dm.ViewContext(view_kind='lesson', active_ref=reference(blocks[0]), selection=dm.Selection(
        ref=ref, exact_quote='错误', start_codepoint=0, end_codepoint=2))
    run = prepare(values, scope)
    assert run.run.status == 'failed' and run.context is None
    assert run.result.error_code in {'TUTOR_CONTEXT_INVALID', 'TUTOR_CONTEXT_CHANGED'}
    assert run.run.answer_markdown == '' and run.latest_proposal_id is None


@pytest.mark.parametrize('texts,expected,reason', [(['条件' * 4000, '条件' * 2500], 1, 'character_budget'),
                                                   (['完整块。'] * 10, 8, 'block_budget')])
def test_context_omits_whole_blocks_and_reports_real_budget(tmp_path, texts, expected, reason):
    values = setup(tmp_path, texts)
    db, identity, blocks, lesson, service = values
    run = prepare(values, dm.ViewContext(view_kind='lesson', active_ref=reference(lesson)))
    assert run.context is not None and run.run.status == 'awaiting_approval'
    assert len(run.context.included) == expected
    assert all(item.reason == reason for item in run.context.omissions)
    with db.transaction(immediate=False) as conn:
        context = service.context.read(conn, identity, run.context.snapshot.id)
        assert [item.text for item in context.evidence] == texts[:expected]
        assert [item.ref for item in context.evidence] == [reference(b) for b in blocks[:expected]]
        assert context.snapshot.character_count <= 12000


def test_changed_actual_body_cannot_dispatch_the_original_preparation(tmp_path):
    values = setup(tmp_path, ['完整的原始条件。'])
    db, identity, blocks, lesson, service = values
    run = prepare(values, dm.ViewContext(view_kind='lesson', active_ref=reference(lesson)))
    assert run.context is not None
    body = db.settings.data_dir / 'blobs' / blocks[0].body_sha256[:2] / blocks[0].body_sha256
    body.write_bytes('被替换的正文'.encode())
    with db.transaction(immediate=False) as conn:
        context = service.context.read(conn, identity, run.context.snapshot.id)
        with pytest.raises(ApiError) as caught:
            service.context.verify(conn, identity, context)
        assert caught.value.code == 'CONTENT_HASH_MISMATCH'


def test_corrupt_private_context_record_is_not_returned_as_a_valid_snapshot(tmp_path):
    values = setup(tmp_path, ['原创冻结内容。'])
    db, identity, _, lesson, service = values
    run = prepare(values, dm.ViewContext(view_kind='lesson', active_ref=reference(lesson)))
    assert run.context is not None
    identifier = run.context.snapshot.id
    with db.transaction() as conn:
        row = conn.execute('SELECT envelope_json FROM context_snapshots WHERE id=?', (identifier,)).fetchone()
        value = json.loads(row[0])
        value['prepared']['messages'][-1]['content'] = '篡改问题'
        conn.execute('UPDATE context_snapshots SET envelope_json=? WHERE id=?', (json.dumps(value), identifier))
    with db.transaction(immediate=False) as conn:
        with pytest.raises(ApiError, match='完整性'):
            service.context.read(conn, identity, identifier)


def prepare_interaction(database, identity, scope, binding, *, key='interaction'):
    service = TutorService(database, ContextService(database))
    thread = service.create_thread(identity, TutorThreadCreate(scope=scope, binding=binding, title='真实交互边界'), key + '-thread')
    ack = service.start(identity, TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id,
        workspace_id=identity.workspace_id, message='请帮助检查当前已保存的思路。', intent='hint', context=scope),
        expected_thread_revision=thread.revision, binding=binding), key + '-run')
    transport = NoTransport()
    assert TutorWorker(database, service.context, transport, build_outbound).run_once()
    run = service.read(identity, ack.run.id)
    assert transport.calls == 0 and run.run.status == 'awaiting_approval' and run.context is not None
    with database.transaction(immediate=False) as conn:
        context = service.context.read(conn, identity, run.context.snapshot.id)
        service.context.verify(conn, identity, context)
    return service, context, json.loads(context.evidence[0].text)


def test_practice_context_uses_saved_response_and_only_explicitly_released_help(tmp_path):
    from services.api.app.application.practice import PracticeService
    from services.api.app.practice_dto import PracticeHintRequest, PracticeSessionCreate, PracticeSolutionRequest
    from services.api.app.tutor_dto import TutorPracticeBinding
    from tests.integration.test_assessment_attempts import storage
    database, identity, fixture, _ = storage.__wrapped__(tmp_path)
    practice = PracticeService(database)
    session = practice.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'practice')
    question = reference(fixture.questions[0])
    response = dm.ResponseDraft(question_id=question.id, answer='真实保存的作答 😀', steps_markdown='先检查条件')
    saved = practice.save_responses(identity, session.id, dm.ResponsesWrite(expected_revision=1, responses=[response]), 'save')
    scope = dm.ViewContext(view_kind='practice', active_ref=reference(fixture.practice))
    binding = TutorContextBinding(practice=TutorPracticeBinding(session_id=session.id,
        session_revision=saved.revision, question_ref=question), assessment=None)
    service, context, material = prepare_interaction(database, identity, scope, binding)
    assert material['saved_response'] == response.model_dump(mode='json')
    assert material['already_released_help'] == [] and material['submitted_result'] is None
    assert all(answer.solution_markdown not in context.evidence[0].text for answer in fixture.solutions)
    hint = practice.hint(identity, session.id, PracticeHintRequest(question_id=question.id,
        expected_revision=saved.revision, level=1), 'hint')
    released = practice.solution(identity, session.id, PracticeSolutionRequest(question_id=question.id,
        expected_revision=hint.revision), 'solution')
    with database.transaction(immediate=False) as conn:
        # Old context stays readable as history, but cannot authorize changed input.
        assert service.context.read(conn, identity, context.snapshot.id) == context
        with pytest.raises(ApiError) as changed:
            service.context.verify(conn, identity, context)
        assert changed.value.code == 'TUTOR_CONTEXT_CHANGED'
    binding.practice.session_revision = released.revision
    _, actual, material = prepare_interaction(database, identity, scope, binding, key='released')
    assert [(item['kind'], item['level']) for item in material['already_released_help']] == [('hint', 1), ('solution', 0)]
    assert material['already_released_help'][1]['markdown'] == fixture.solutions[0].solution_markdown
    assert all(answer.solution_markdown not in actual.evidence[0].text for answer in fixture.solutions[1:])


def test_assisted_context_binds_actual_question_without_private_standard_or_other_scope(tmp_path):
    from services.api.app.tutor_dto import TutorAssessmentBinding
    from tests.integration.test_assessment_attempts import storage, start
    database, identity, fixture, assessment = values = storage.__wrapped__(tmp_path)
    attempt = start(values, mode='assisted')
    question = reference(fixture.questions[0])
    response = dm.ResponseDraft(question_id=question.id, answer='保存的辅助测试答案')
    saved = assessment.save_responses(identity, attempt.id, dm.ResponsesWrite(expected_revision=1, responses=[response]), 'save')
    scope = dm.ViewContext(view_kind='assessment_help', active_ref=reference(fixture.assessment), attempt_id=attempt.id)
    binding = TutorContextBinding(practice=None, assessment=TutorAssessmentBinding(attempt_revision=saved.revision,
        question_ref=question, grading_revision=None))
    service, context, material = prepare_interaction(database, identity, scope, binding)
    assert material['saved_response'] == response.model_dump(mode='json') and material['released_feedback'] is None
    assert all(answer.solution_markdown not in context.evidence[0].text for answer in fixture.solutions)
    with database.transaction(immediate=False) as conn:
        with pytest.raises(ApiError) as other:
            service.context.check_scope(conn, identity, dm.ViewContext(view_kind='lesson', active_ref=reference(fixture.lesson)),
                TutorContextBinding(practice=None, assessment=None))
        assert other.value.code == 'POLICY_DENIED'
    assessment.save_responses(identity, attempt.id, dm.ResponsesWrite(expected_revision=saved.revision, responses=[]), 'changed')
    with database.transaction(immediate=False) as conn:
        with pytest.raises(ApiError) as changed:
            service.context.verify(conn, identity, context)
        assert changed.value.code == 'TUTOR_CONTEXT_CHANGED'


@pytest.mark.parametrize('mode,code', [('open_book', 'POLICY_DENIED'), ('independent', 'ASSESSMENT_ACTIVE')])
def test_current_assessment_policy_denies_tutor_before_thread_allocation(tmp_path, mode, code):
    from tests.integration.test_assessment_attempts import storage, start
    database, identity, fixture, _ = values = storage.__wrapped__(tmp_path)
    start(values, mode=mode)
    service = TutorService(database, ContextService(database))
    with database.connect() as conn:
        before = conn.execute('SELECT COUNT(*) FROM tutor_threads').fetchone()[0]
    with pytest.raises(ApiError) as denied:
        service.create_thread(identity, TutorThreadCreate(scope=dm.ViewContext(view_kind='lesson', active_ref=reference(fixture.lesson)),
            binding=TutorContextBinding(practice=None, assessment=None), title='拒绝的学科线程'), 'denied')
    assert denied.value.code == code
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM tutor_threads').fetchone()[0] == before
    if mode == 'open_book':
        # The new Tutor restriction does not block the existing public material owner.
        with database.transaction(immediate=False) as conn:
            assert service.context.content.exact(conn, identity, reference(fixture.lesson)) == fixture.lesson


def test_independent_review_requires_actual_complete_grade_then_exact_released_question(tmp_path):
    from services.api.app.application.grading import GradingService, GradingWorker
    from services.api.app.tutor_dto import TutorAssessmentBinding
    from tests.integration.test_assessment_attempts import storage, start
    from tests.integration.test_assessment_grading import real_author, review_request
    database, identity, fixture, assessment = values = storage.__wrapped__(tmp_path)
    attempt = start(values)
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'submit')
    worker = GradingWorker(database)
    assert worker.run_once()
    record = assessment.get_attempt(identity, attempt.id)
    scope = dm.ViewContext(view_kind='assessment_review', active_ref=reference(fixture.assessment), attempt_id=attempt.id)
    binding = TutorContextBinding(practice=None, assessment=TutorAssessmentBinding(attempt_revision=record.revision,
        question_ref=reference(fixture.questions[0]), grading_revision=1))
    service = TutorService(database, ContextService(database))
    with pytest.raises(ApiError) as denied:
        service.create_thread(identity, TutorThreadCreate(scope=scope, binding=binding, title='尚未完成的评分'), 'pending')
    assert denied.value.code == 'ASSESSMENT_ANSWER_PROTECTED'
    GradingService(database).regrade(real_author(database), attempt.id, review_request(fixture), 'human-review')
    assert worker.run_once()
    record = assessment.get_attempt(identity, attempt.id)
    binding.assessment.attempt_revision = record.revision
    binding.assessment.grading_revision = 2
    _, context, material = prepare_interaction(database, identity, scope, binding)
    assert material['grading_revision'] == 2
    assert material['released_feedback']['question_ref'] == reference(fixture.questions[0]).model_dump(mode='json')
    assert material['released_feedback']['solution_markdown'] == fixture.solutions[0].solution_markdown
    assert all(answer.solution_markdown not in context.evidence[0].text for answer in fixture.solutions[1:])
    with database.connect() as conn:
        assert {row[0] for row in conn.execute('SELECT review_status FROM solutions')} == {'needs_review'}
