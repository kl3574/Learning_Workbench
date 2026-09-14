import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { SubmittedResponse } from '../grading/SubmittedResponse'
import { reviewSnapshot } from './review.testdata'
vi.mock('../../shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <p>{children}</p> }))
afterEach(cleanup)
test('renders the frozen submitted answer and original Unicode steps as inert text, with no editable response control', async () => { const snapshot = reviewSnapshot(); render(<SubmittedResponse index={0} question={snapshot.questions[0]} questionRef={snapshot.preflight.prior_seen.questions[0].question_ref} response={{ question_id: snapshot.questions[0].id, answer: '<script>original 🧠é</script>', steps_markdown: '原步骤\n\\alpha < beta\n**原样保存**' }} />); await screen.findByText('原创合成题面'); expect(screen.getByLabelText('第 1 题已提交答案').textContent).toBe('<script>original 🧠é</script>'); expect(screen.getByLabelText('第 1 题已提交推导步骤').textContent).toBe('原步骤\n\\alpha < beta\n**原样保存**'); expect(document.querySelectorAll('script,textarea,input')).toHaveLength(0) })
