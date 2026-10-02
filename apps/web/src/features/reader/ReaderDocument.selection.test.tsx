import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import { emptySession, openTab } from '../../workbench/model'
import { readerContext } from './target'
import { versions } from './versionCompare/fixtures'
import { ReaderDocument } from './ReaderDocument'

// Isolate the real Reader textarea and its selection callback. Content transport,
// rendered Markdown selection and the other panels have separate owner tests.
const source = vi.hoisted(() => ({ course: vi.fn(), lesson: vi.fn(), block: vi.fn(), progress: vi.fn(), current: vi.fn() }))
vi.mock('../../api/client', () => ({ request: (...args: unknown[]) => source.current(...args) }))
vi.mock('./contentClient', () => ({ readCourse: (...args: unknown[]) => source.course(...args), readLesson: (...args: unknown[]) => source.lesson(...args), readBlock: (...args: unknown[]) => source.block(...args), readProgress: (...args: unknown[]) => source.progress(...args) }))
vi.mock('../../shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <p>{children}</p> }))
vi.mock('./SourcePanel', () => ({ SourcePanel: () => null }))
vi.mock('./versionCompare/BlockVersionCompare', () => ({ BlockVersionCompare: () => null }))
vi.mock('../draftEditor/DraftEditor', () => ({ DraftEditor: () => null }))
afterEach(() => { cleanup(); localStorage.clear(); vi.clearAllMocks() })

test.each(['\n', '\r\n', '\r'])('the actual Reader textarea preserves raw %j source offsets after a non-BMP prefix', async newline => {
  const course: ContentRef = { entity: 'course', id: 'course_source_selection', revision: 1, sha256: 'c'.repeat(64) }
  const lesson: ContentRef = { entity: 'lesson', id: 'lesson_source_selection', revision: 1, sha256: 'd'.repeat(64) }
  const block = versions[0], body = `🧠 prefix${newline}target${newline}tail`
  source.course.mockResolvedValue({ id: course.id, title: 'Synthetic course', lesson_refs: [lesson], sections: [] })
  source.lesson.mockResolvedValue({ id: lesson.id, title: 'Synthetic lesson', block_refs: [block.ref] })
  source.block.mockResolvedValue({ ...block.data, body })
  source.progress.mockResolvedValue({ revision: 1, readings: [], bookmarks: [] })
  source.current.mockResolvedValue(lesson)
  const session = openTab({ ...emptySession(), course_ref: course }, readerContext({ course, lesson }), true, () => false)
  const selected = vi.fn(), noop = () => undefined
  render(<ReaderDocument session={session} workspace="workspace_source_selection" onOpen={noop} onScroll={noop} onSelect={selected} onNote={noop} onLoaded={noop} progressVersion={0} progressChanged={noop} onAux={noop} loadSynthetic={noop} practice={noop} />)
  const input = await screen.findByLabelText(`原始 Markdown：${block.data.block.title}`) as HTMLTextAreaElement
  fireEvent.click(screen.getByText('原始 Markdown 与精确选文', { exact: true }))
  expect(input.value).toBe(body.replace(/\r\n|\r/g, '\n'))
  input.focus(); const start = input.value.indexOf('target')
  input.setSelectionRange(start, start + 6); fireEvent.select(input)
  expect(selected).toHaveBeenLastCalledWith({ ref: block.ref, exact_quote: 'target', prefix: `🧠 prefix${newline}`, suffix: `${newline}tail`, start_codepoint: Array.from(`🧠 prefix${newline}`).length, end_codepoint: Array.from(`🧠 prefix${newline}target`).length })
  // A selection spanning the normalized line break retains the original bytes.
  input.setSelectionRange(start, input.value.length); fireEvent.select(input)
  expect(selected).toHaveBeenLastCalledWith({ ref: block.ref, exact_quote: `target${newline}tail`, prefix: `🧠 prefix${newline}`, suffix: '', start_codepoint: Array.from(`🧠 prefix${newline}`).length, end_codepoint: Array.from(body).length })
})
