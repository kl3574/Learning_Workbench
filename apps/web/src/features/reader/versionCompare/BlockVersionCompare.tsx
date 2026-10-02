import { useMemo, useState } from 'react'
import type { ContentRef } from '../../../../../../packages/contracts/generated/api-types'
import { canonical } from '../../retrieval/retrievalModel'
import type { LoadedBlock } from '../contentClient'
import { compareClient, type ComparePort } from './compareClient'
import { boundedLineDiff } from './boundedDiff'
import { useVersionCompare } from './useVersionCompare'
import { RestorePanel, type RestoreStatus } from '../../contentRestore/RestorePanel'
import './versionCompare.css'

const fields = ['kind', 'title', 'body_path', 'body_sha256', 'concepts', 'citations', 'depends_on'] as const
const labels = { kind: '块类型', title: '标题', body_path: '正文逻辑路径', body_sha256: '正文 SHA-256', concepts: '概念 ID', citations: '引用 ID', depends_on: '精确依赖' }
function SourceScope({ value }: { value: LoadedBlock }) {
  return <div className="compare-source"><p>元数据 SHA-256：<code>{value.block_ref.sha256}</code></p><p>正文 SHA-256：<code>{value.block.body_sha256}</code></p>
    {value.original_source ? <p>原件绑定：{value.original_source.source.media_type} · <code>{value.original_source.source.sha256}</code>；{value.original_source.original_access === 'allowed' ? '当前允许读取原件' : value.original_source.original_access === 'author_required' ? '原件需作者权限' : '原件不可读取'}</p> : <p>无已解析原件绑定。</p>}
    <p>已解析引用 {value.citations.length} 条；未解析引用 {value.unresolved_citation_ids.length} 条。来源记录不等于独立核实。</p>
    {value.citations.map(item => <p key={item.citation.id}>{item.citation.id} · {item.citation.title} · {item.citation.locator} · {item.citation.verification}</p>)}
    {value.unresolved_citation_ids.length > 0 && <p>未解析 ID：{value.unresolved_citation_ids.join('、')}</p>}
    {value.warnings.map((warning, index) => <p key={index}>{warning.code} · {warning.message}</p>)}
  </div>
}
export function BlockVersionCompare({ workspace, blockRef, port = compareClient, paused = true, onRestoreState }: { workspace: string | null; blockRef: ContentRef; port?: ComparePort; paused?: boolean; onRestoreState?: (value: RestoreStatus) => void }) {
  const restoreScope = JSON.stringify([workspace, blockRef.id])
  const [openRestoreScope, setOpenRestoreScope] = useState(''), [choice, setChoice] = useState<{ scope: string; ref: ContentRef } | null>(null)
  const source = choice?.scope === restoreScope ? choice.ref : null
  const [restoreStatus, setRestoreStatus] = useState<RestoreStatus>({ dirty: false, safe: true, closeSafe: true })
  const state = useVersionCompare(workspace, blockRef.id, port)
  const diff = useMemo(() => state.result ? boundedLineDiff(state.result[0].body, state.result[1].body) : null, [state.result])
  const refs = [...state.items.map(item => item.ref)]
  for (const selected of [state.left, state.right]) if (selected && !refs.some(ref => ref.sha256 === selected.sha256)) refs.push(selected)
  return <section className="block-version-compare" aria-label="块修订比较">
    <button disabled={!workspace || blockRef.entity !== 'block'} aria-expanded={state.open} onClick={state.open ? state.close : state.show}>{state.open ? '收起修订比较' : '比较此块的两个修订'}</button>
    {state.open && <div className="compare-content"><h3>比较同一块的两个精确修订</h3><p>明确选择两侧修订。仅比较原文与字段；文字差异不证明数学或语义等价，不批准、发布或恢复内容。</p><p>收起保留本页选择，正文重新读取；切到其他块或刷新页面需重新选择。</p>
      <div className="compare-controls">{(['left', 'right'] as const).map(side => <label key={side}>{side === 'left' ? '左侧修订' : '右侧修订'}<select value={state[side]?.sha256 ?? ''} onChange={event => state.choose(side, event.target.value)}><option value="">请选择准确修订</option>{refs.map(ref => <option key={ref.sha256} value={ref.sha256}>修订 {ref.revision} · {ref.sha256.slice(0, 12)}</option>)}</select></label>)}</div>
      <div className="compare-actions"><button disabled={state.busy} onClick={() => void state.history()}>重新读取历史列表</button>{state.cursor && <button disabled={state.busy || state.items.length >= 200} onClick={() => void state.history(true)}>加载更多修订</button>}<button disabled={state.busy || !state.left || !state.right || state.left.sha256 === state.right.sha256} onClick={() => void state.read()}>读取所选两个修订</button></div>
      {state.cursor && state.items.length >= 200 && <p>本次历史列表最多保留 200 项，尚有历史未列出；没有用当前版本替代所选修订。</p>}
      {state.busy && <p role="status">正在核对权限和准确修订…</p>}{state.error && <p role="alert">{state.error}</p>}
      {state.result && <><div className="compare-columns">{state.result.map((value, index) => <section key={index} aria-label={index ? '右侧版本' : '左侧版本'}><h4>{index ? '右侧' : '左侧'} · 修订 {value.block_ref.revision}</h4><p><code>{value.block_ref.id}</code> · {value.block.title}</p><SourceScope value={value} /><button disabled={paused || restoreStatus.dirty || !restoreStatus.closeSafe} onClick={() => { setChoice({ scope: restoreScope, ref: value.block_ref }); setOpenRestoreScope(restoreScope) }}>选择{index ? '右侧' : '左侧'}历史版本准备恢复</button></section>)}</div>
        <h4>字段差异</h4>{fields.filter(field => canonical(state.result![0].block[field]) !== canonical(state.result![1].block[field])).map(field => <div className="compare-field" key={field}><strong>{labels[field]}</strong><div className="compare-columns"><pre aria-label={`左侧${labels[field]}`}>{JSON.stringify(state.result![0].block[field], null, 2)}</pre><pre aria-label={`右侧${labels[field]}`}>{JSON.stringify(state.result![1].block[field], null, 2)}</pre></div></div>)}
        <h4>原文差异</h4>{diff?.kind === 'parallel' ? <p role="status">{diff.reason}</p> : <><p>按完整行保留相同的开头和结尾；变化的中段整体标记增删，未推断公式含义。</p><div className="compare-diff" aria-label="逐行文字差异">{diff?.changes.map((change, index) => <div className={`compare-${change.kind}`} key={index}><strong>{change.kind === 'added' ? '右侧新增' : change.kind === 'removed' ? '左侧删除' : '相同行'}</strong><pre>{change.text}</pre></div>)}</div></>}
        <div className="compare-columns compare-originals">{state.result.map((value, index) => <section key={index}><h4>{index ? '右侧' : '左侧'}完整原文</h4><pre tabIndex={0} aria-label={index ? '右侧完整原文' : '左侧完整原文'}>{value.body}</pre></section>)}</div>
      </>}
    </div>}
    {workspace && <><button onClick={() => setOpenRestoreScope(restoreScope)}>打开此块的恢复原记录</button>{openRestoreScope === restoreScope && <RestorePanel key={workspace + ':' + blockRef.id} workspace={workspace} blockId={blockRef.id} selectedSource={source} paused={paused} onState={value => { setRestoreStatus(value); onRestoreState?.(value) }} />}</>}
  </section>
}
