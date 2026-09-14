import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { memo, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import { mathSvg } from './math'
function Formula({ source, display }: { source: string; display: boolean }) {
  const key = useMemo(() => bytesToHex(sha256(new TextEncoder().encode(source))), [source])
  const result = useMemo(() => { try { return { svg: mathSvg(source, display), error: '' } } catch (e) { return { svg: '', error: (e as Error).message } } }, [source, display])
  if (result.error) return <span className="math-error" role="alert">{result.error}；原始 LaTeX：<code>{source}</code></span>
  return <span className={display ? 'formula display' : 'formula inline'} aria-label={`公式：${source}`} tabIndex={display ? 0 : undefined} data-tex={source} data-focus-key={display ? `formula-${key}` : undefined}><span aria-hidden="true" dangerouslySetInnerHTML={{ __html: result.svg }} />{display && <details className="tex-source" data-view-key={`tex-${key}`}><summary data-focus-key={`tex-summary-${key}`}>LaTeX 源文</summary><code>{source}</code></details>}</span>
}
export const Markdown = memo(function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} skipHtml components={{
    code({ className, children: content, ...rest }) { const source = String(content).replace(/\n$/, ''); return className?.includes('math-') ? <Formula source={source} display={className.includes('math-display')} /> : <code className={className} {...rest}>{content}</code> },
    pre({ children: content }) { return <div className="code-or-math">{content}</div> },
    img({ alt }) { return <span className="muted">[图片未加载：{alt ?? '无描述'}]</span> },
    a({ href, children: content }) { return <a href={href} rel="noopener noreferrer" target="_blank">{content}</a> },
  }}>{children}</ReactMarkdown>
})
