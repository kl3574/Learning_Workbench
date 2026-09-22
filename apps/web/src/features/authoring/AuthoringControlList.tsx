import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
/** The control surface deliberately renders only safe identity/status fields. */
export function AuthoringControlList({ jobs, busy, academic, read, cancel }: { jobs: JobSnapshot[]; busy: boolean; academic: boolean; read: (id: string) => void; cancel: (job: JobSnapshot) => void }) {
  return <section aria-label="创作任务安全控制"><h3>已有创作与数值任务</h3><p>这里只显示任务状态。取消请求不保证远端尚未执行，也不撤销已发生的计算。</p>
    {!jobs.length && <p>本页没有任务。</p>}
    {jobs.map(job => <article key={job.id}><p>{job.id} · {job.status} · r{job.revision}</p><p>{job.kind === 'authoring_numeric_check' ? '独立数值检查任务' : '例题候选生成任务'}</p>
      <button disabled={busy || ['completed', 'failed', 'cancelled'].includes(job.status)} onClick={() => cancel(job)}>明确取消任务 {job.id}</button>
      {academic && job.kind === 'authoring' && <button disabled={busy} onClick={() => read(job.id)}>读取创作详情 {job.id}</button>}
    </article>)}
  </section>
}
