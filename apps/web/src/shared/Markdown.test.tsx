import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { Markdown } from './Markdown'
import { mathSvg } from './math'
afterEach(cleanup)
describe('local safe mathematics and AST projection', () => {
  it('renders actual MathJax SVG with preserved TeX', () => { const { container } = render(<Markdown>{'$$\nx^2+1\\geq 1\n$$'}</Markdown>); expect(container.querySelector('svg')).not.toBeNull(); expect(container.querySelector('[data-tex]')?.getAttribute('data-tex')).toBe('x^2+1\\geq 1') })
  it('does not project raw HTML, scripts, active images or javascript links', () => { const { container } = render(<Markdown>{'<script>window.evil=true</script>\n\n<img src="https://example.invalid/a" onerror="evil()">\n\n[attack](javascript:evil())\n\n![remote](https://example.invalid/image)'}</Markdown>); expect(container.querySelector('script,img')).toBeNull(); expect(container.innerHTML).not.toContain('javascript:') })
  it('rejects dynamic TeX macros and external resources without losing source', () => { for (const source of ['\\require{html}', '\\href{https://example.invalid}{x}', '\\def\\a{x}', 'x'.repeat(12001)]) expect(() => mathSvg(source, false)).toThrow(); const { container } = render(<Markdown>{'$\\require{html}$'}</Markdown>); expect(container.textContent).toContain('原'); expect(container.querySelector('svg')).toBeNull() })
})
