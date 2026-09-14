import type { ResponseDraft } from '../../../../../packages/contracts/generated/types'
export function ResponseText({ values }: { values: ResponseDraft[] | null }) {
  return values === null ? <p>原基准未知，不能推测。</p> : !values.length ? <p>尚无作答。</p> : <dl>{values.map(value => <div key={value.question_id}><dt>{value.question_id}</dt><dd><pre>{value.answer || '（空答案）'}</pre><span>推导步骤</span><pre>{value.steps_markdown || '（无步骤）'}</pre></dd></div>)}</dl>
}
export function ResponseComparison({ base, local, remote, remoteLabel = '服务端作答' }: { base: ResponseDraft[] | null; local: ResponseDraft[]; remote: ResponseDraft[]; remoteLabel?: string }) {
  return <div className="practice-comparison">{([{ name: '原基准作答', values: base }, { name: '当前页面作答', values: local }, { name: remoteLabel, values: remote }]).map(column => <section key={column.name}><h3>{column.name}</h3><div tabIndex={0} aria-label={column.name}><ResponseText values={column.values} /></div></section>)}</div>
}
