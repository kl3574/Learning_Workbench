import { lazy, Suspense, useEffect, useRef, useState, type RefObject } from 'react'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { getSessionGeneration, request } from '../../api/client'
import type { DraftSnapshot, SourceSnapshot } from './contracts'
import { controlledDownloadPath } from './recovery'
import { SourceProvenance } from './SourceProvenance'

const Markdown = lazy(() => import('../../shared/Markdown').then(module => ({ default: module.Markdown })))

function CandidateContent({ draft }: { draft: DraftSnapshot }) {
  const payload = draft.payload
  if ('metadata' in payload) return <><p className="muted">内容块候选 · {payload.metadata.title}</p><Suspense fallback={<p role="status">正在加载正文排版…</p>}><Markdown>{payload.body_markdown}</Markdown></Suspense></>
  if ('stem_markdown' in payload) return <><h3>公开题面候选</h3><Suspense fallback={<p role="status">正在加载题面…</p>}><Markdown>{payload.stem_markdown}</Markdown></Suspense></>
  return <>
    {'title' in payload && <h3>{payload.title}</h3>}
    {'audience' in payload && <p>学习对象：{payload.audience}</p>}
    {'objectives' in payload && <><p>学习目标</p><ul>{(payload.objectives ?? []).map((objective, index) => <li key={index}>{objective}</li>)}</ul></>}
    {'lesson_refs' in payload && <><p>包含 {payload.lesson_refs.length} 个小节候选。请切换候选检查每个内容块。</p><ul className="import-preview-list">{payload.lesson_refs.map(ref => <li key={ref.id}>{ref.id} · 修订 {ref.revision}</li>)}</ul></>}
    {'block_refs' in payload && <><p>包含 {payload.block_refs.length} 个内容块候选。</p><ul className="import-preview-list">{payload.block_refs.map(ref => <li key={ref.id}>{ref.id} · 修订 {ref.revision}</li>)}</ul></>}
    {'question_refs' in payload && <p>包含 {payload.question_refs.length} 个公开题面引用。</p>}
    {'prerequisite_ids' in payload && (payload.prerequisite_ids?.length ?? 0) > 0 && <p>先修概念：{payload.prerequisite_ids?.join('、')}</p>}
    {'steps' in payload && <ol>{payload.steps.map(step => <li key={step.id}>{step.title} · {step.target.id}</li>)}</ol>}
  </>
}

function OriginalDownload({ source, accessEpoch }: { source: SourceSnapshot; accessEpoch: RefObject<number> }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(true)
  const urls = useRef(new Set<string>())
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear() }
  }, [])
  const download = async () => {
    setBusy(true); setError('')
    const epoch = accessEpoch.current, access = getSessionGeneration()
    try {
      const artifact = source.artifact
      const path = controlledDownloadPath(artifact.download_path, location.origin)
      if (path !== `/api/v1/artifacts/${artifact.artifact_id}/download`) throw new Error('原件地址与服务端文件标识不一致。')
      const blob = await request('GET /api/v1/artifacts/{id}/download', undefined, undefined, { path: { id: artifact.artifact_id } })
      if (!mounted.current || epoch !== accessEpoch.current || access !== getSessionGeneration()) return
      if (blob.size !== artifact.size || bytesToHex(sha256(new Uint8Array(await blob.arrayBuffer()))) !== artifact.sha256) throw new Error('原件字节或哈希校验失败，未生成下载文件。')
      if (!mounted.current || epoch !== accessEpoch.current || access !== getSessionGeneration()) return
      // Other browser profiles do not share access broadcasts. Recheck the
      // current server guard before initiating a download of earlier bytes.
      const current = await request('GET /api/v1/sources/{id}', undefined, undefined, { path: { id: source.id } })
      if (!mounted.current || epoch !== accessEpoch.current || access !== getSessionGeneration()) return
      if (current.id !== source.id || current.sha256 !== source.sha256 || current.size !== source.size || current.artifact.artifact_id !== artifact.artifact_id || current.artifact.sha256 !== artifact.sha256 || current.artifact.size !== artifact.size) throw new Error('原件引用已变化，未生成下载文件。请重新读取来源。')
      const url = URL.createObjectURL(blob)
      urls.current.add(url)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = artifact.filename; anchor.click()
      setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 60000)
    } catch (reason) { if (mounted.current && epoch === accessEpoch.current && access === getSessionGeneration()) setError(reason instanceof Error ? reason.message : '原件下载未完成。') }
    finally { if (mounted.current) setBusy(false) }
  }
  return <div><div className="import-buttons"><button type="button" disabled={busy} onClick={() => void download()}>{busy ? '正在校验原件…' : '下载受控原件'}</button><small>{source.media_type} · {source.size} 字节</small></div>{error && <p role="alert" className="import-error">{error}</p>}</div>
}

export function DraftPreview({ ids, selected, draft, source, sourceError, accessEpoch, loading, error, choose }: {
  ids: string[]; selected: string; draft: DraftSnapshot | null; source: SourceSnapshot | null;
  accessEpoch: RefObject<number>;
  loading: boolean; error: string; sourceError: string; choose: (id: string) => void;
}) {
  const index = ids.indexOf(selected)
  return <section aria-label="候选正文预览"><h3>候选正文预览</h3><p className="muted">这里展示暂存候选。候选 ID 不代表正式发布或内容审核通过。</p>
    <label>选择预览候选<select value={selected} onChange={event => choose(event.target.value)}>{ids.map((id, position) => <option key={id} value={id}>候选 {position + 1} / {ids.length} · {id}</option>)}</select></label>
    <div className="import-buttons"><button disabled={index <= 0 || loading} onClick={() => choose(ids[index - 1])}>上一候选</button><button disabled={index < 0 || index >= ids.length - 1 || loading} onClick={() => choose(ids[index + 1])}>下一候选</button></div>
    {loading && <p role="status">读取候选正文…</p>}
    {error && <div className="import-error" role="alert"><p>{error}</p><button onClick={() => choose(selected)}>重试读取候选</button></div>}
    {draft && <><div className="import-preview" tabIndex={0} aria-label="当前候选正文"><CandidateContent draft={draft} /></div><details><summary>候选修订与校验信息</summary><dl className="import-details"><dt>候选 ID</dt><dd>{draft.id}</dd><dt>候选对象 ID</dt><dd>{'metadata' in draft.payload ? draft.payload.metadata.id : draft.payload.id}</dd><dt>候选修订</dt><dd>{draft.revision}</dd><dt>候选 SHA-256</dt><dd><code className="import-hash">{draft.candidate_sha256}</code></dd></dl></details></>}
    {draft && 'metadata' in draft.payload && <SourceProvenance citations={draft.payload.citations ?? []} />}
    {sourceError && <div className="import-warning" role="status"><p>原件暂不可读取：{sourceError}</p><p>安全候选正文已单独读取。需要作者权限时，可在窗口顶部显式切换角色；这不会自动认证候选内容。</p><button type="button" disabled={loading} onClick={() => choose(selected)}>重试读取原件信息</button></div>}
    {source && <OriginalDownload key={source.id} source={source} accessEpoch={accessEpoch} />}
  </section>
}
