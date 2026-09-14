import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { DraftConflictPreview } from './DraftConflictPreview'

afterEach(cleanup)

describe('draft conflict preview', () => {
  it('shows the actual stored text separately from the current page and original base', () => {
    const view = render(<DraftConflictPreview base="原始问题" local="当前窗口的候选" stored="另一窗口已保存的版本" />)
    expect(view.getByRole('region', { name: '原基准正文' }).textContent).toBe('原始问题')
    expect(view.getByRole('region', { name: '当前页面正文' }).textContent).toBe('当前窗口的候选')
    expect(view.getByRole('region', { name: '已存草稿正文' }).textContent).toBe('另一窗口已保存的版本')
    expect(view.queryByRole('button')).toBeNull()
    expect(view.queryByRole('textbox')).toBeNull()
  })

  it('distinguishes an unknown base from an intentionally empty version', () => {
    const view = render(<DraftConflictPreview base={null} local="" stored="已保存的问题" />)
    expect(view.getByText('原基准未知，无法判断相对原基准的改动。')).not.toBeNull()
    expect(view.queryByRole('region', { name: '原基准正文' })).toBeNull()
    expect(view.getByRole('region', { name: '当前页面正文' }).textContent).toBe('（空草稿）')
    view.rerender(<DraftConflictPreview base="" local="新的问题" stored="已保存的问题" />)
    expect(view.getByRole('region', { name: '原基准正文' }).textContent).toBe('（空草稿）')
    expect(view.queryByText('原基准未知，无法判断相对原基准的改动。')).toBeNull()
  })

  it('preserves multiline source as inert text and permits keyboard access to each scroll region', () => {
    const text = '<img src=x onerror=alert(1)>\n第二行 🧭\n' + '长'.repeat(2000)
    const view = render(<DraftConflictPreview base="基准" local={text} stored="已存" />)
    expect(view.getByRole('region', { name: '当前页面正文' }).textContent).toBe(text)
    expect(view.container.querySelector('img,script')).toBeNull()
    for (const label of ['原基准', '当前页面', '已存草稿']) {
      const region = view.getByRole('region', { name: `${label}正文` })
      region.focus()
      expect(document.activeElement).toBe(region)
    }
  })
})
