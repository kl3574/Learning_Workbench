import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { memo, useLayoutEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import { mathSvg } from './math'
function Formula({ source, display, identity = '' }: { source: string; display: boolean; identity?: string }) {
  const element = useRef<HTMLSpanElement>(null)
  const [overflow, setOverflow] = useState(false)
  useLayoutEffect(() => { const node = element.current; if (!node) return; const measure = () => setOverflow(node.scrollWidth > node.clientWidth + 1); measure(); if (typeof ResizeObserver === 'undefined') return; const observer = new ResizeObserver(measure); observer.observe(node); return () => observer.disconnect() }, [source, display])
  const key = useMemo(() => bytesToHex(sha256(new TextEncoder().encode(identity + source))), [source, identity])
  const result = useMemo(() => { try { return { svg: mathSvg(source, display), error: '' } } catch (e) { return { svg: '', error: (e as Error).message } } }, [source, display])
  if (result.error) return <span className="math-error" role="alert">{result.error}；原始 LaTeX：<code>{source}</code></span>
  return <span ref={element} className={display ? 'formula display' : 'formula inline'} aria-label={`公式：${source}`} tabIndex={display || overflow ? 0 : undefined} data-tex={source} data-focus-key={display || overflow ? `formula-${key}` : undefined}><span aria-hidden="true" dangerouslySetInnerHTML={{ __html: result.svg }} />{display && <details className="tex-source" data-view-key={`tex-${key}`}><summary data-focus-key={`tex-summary-${key}`}>LaTeX 源文</summary><code>{source}</code></details>}</span>
}
type SourceNode = { type: string; value?: string; tagName?: string; properties?: Record<string, unknown>; children?: SourceNode[]; position?: { start: { offset?: number }; end: { offset?: number } } }
function sourcePositions() {
  return (root: SourceNode) => {
    const visit = (node: SourceNode) => {
      if (!node.children || ['code', 'pre', 'svg'].includes(node.tagName ?? '')) return
      node.children = node.children.map(child => {
        if (child.type === 'text' && child.value && child.position?.start.offset !== undefined && child.position.end.offset !== undefined) return { type: 'element', tagName: 'span', properties: { 'data-source-start': child.position.start.offset, 'data-source-end': child.position.end.offset }, children: [child] }
        visit(child); return child
      })
    }
    visit(root)
  }
}
export const Markdown = memo(function Markdown({ children, sourceKey }: { children: string; sourceKey?: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={sourceKey ? [sourcePositions] : []} skipHtml components={{
    code({ className, children: content, node, ...rest }) { const source = String(content).replace(/\n$/, ''); return className?.includes('math-') ? <Formula source={source} display={className.includes('math-display')} identity={sourceKey ? `${sourceKey}:${node?.position?.start.offset ?? ''}:` : ''} /> : <code className={className} {...rest}>{content}</code> },
    pre({ children: content }) { return <div className="code-or-math">{content}</div> },
    img({ alt }) { return <span className="muted">[图片未加载：{alt ?? '无描述'}]</span> },
    a({ href, children: content }) { return <a href={href} rel="noopener noreferrer" target="_blank">{content}</a> },
  }}>{children}</ReactMarkdown>
})
