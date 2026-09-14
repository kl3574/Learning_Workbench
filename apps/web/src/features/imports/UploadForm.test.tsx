import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { UploadForm } from './UploadForm'

afterEach(cleanup)

it.each(['pdf', 'docx'])('offers the real %s upload while explaining extraction limits', async kind => {
  const submit = vi.fn(async () => {})
  render(<UploadForm disabled={false} courses={[]} moreCourses={false} onMoreCourses={() => {}} submit={submit} />)
  const file = new File(['original test bytes'], `original.${kind}`)
  fireEvent.change(screen.getByLabelText('选择导入文件'), { target: { files: [file] } })
  fireEvent.change(screen.getByLabelText('解析格式'), { target: { value: kind } })
  expect(screen.getByText(kind === 'pdf' ? /默认不运行 OCR/ : /不会据此猜造 TeX/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '上传并生成预览' }))
  expect(submit).toHaveBeenCalledWith(file, kind, '')
})

it('suspending access removes file details from the DOM and retains the original File and choices in memory', () => {
  const submit = vi.fn(async () => {})
  const props = { disabled: false, courses: [], moreCourses: false, onMoreCourses: () => {}, submit }
  const view = render(<UploadForm {...props} />)
  const file = new File(['original local bytes'], 'original-local.txt')
  fireEvent.change(screen.getByLabelText('选择导入文件'), { target: { files: [file] } })
  fireEvent.change(screen.getByLabelText('解析格式'), { target: { value: 'text' } })
  view.rerender(<UploadForm {...props} suspended />)
  expect(view.container.textContent).toBe('')
  expect(screen.queryByRole('button', { name: '上传并生成预览' })).toBeNull()
  view.rerender(<UploadForm {...props} />)
  expect(screen.getByText(/original-local.txt/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '上传并生成预览' }))
  expect(submit).toHaveBeenCalledWith(file, 'text', '')
})
