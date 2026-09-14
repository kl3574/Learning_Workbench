import { useEffect, useRef, useState } from 'react'
import { bytesToHex } from '@noble/hashes/utils.js'
import { sha256 } from '@noble/hashes/sha2.js'
import { getSessionGeneration, request } from '../../api/client'
import { sourceLocatorLabel } from '../imports/SourceProvenance'
import { controlledDownloadPath } from '../imports/recovery'
import type { LoadedBlock } from './contentClient'
export function SourcePanel({ value, refresh }: { value: LoadedBlock; refresh: () => void }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const alive = useRef(true)
  const epoch = useRef(0)
  const urls = useRef(new Set<string>())
  useEffect(() => { alive.current = true; epoch.current++; return () => { alive.current = false; epoch.current++; for (const url of urls.current) URL.revokeObjectURL(url) } }, [value.block_ref.sha256])
  const original = value.original_source
  const download = async (expected: NonNullable<LoadedBlock['original_source']>['source']) => {
    setError(''); setBusy(true)
    const generation = epoch.current
    const authGeneration = getSessionGeneration()
    try {
      const source = await request('GET /api/v1/sources/{id}', undefined, undefined, { path: { id: expected.id } })
      const artifact = source.artifact
      if (source.id !== expected.id || source.sha256 !== expected.sha256 || source.size !== expected.size || artifact.sha256 !== expected.sha256 || artifact.size !== expected.size) throw new Error('返回的原件与此准确内容块冻结的来源不符，未下载。')
      if (controlledDownloadPath(artifact.download_path, location.origin) !== `/api/v1/artifacts/${artifact.artifact_id}/download`) throw new Error('原件下载地址不匹配。')
      const blob = await request('GET /api/v1/artifacts/{id}/download', undefined, undefined, { path: { id: artifact.artifact_id } })
      if (blob.size !== artifact.size || bytesToHex(sha256(new Uint8Array(await blob.arrayBuffer()))) !== artifact.sha256) throw new Error('原件字节哈希不符，未下载。')
      if (!alive.current || generation !== epoch.current || authGeneration !== getSessionGeneration()) return
      // Workspace roles can also change in another browser profile, outside this page's channel.
      const permission = await request('GET /api/v1/sources/{id}', undefined, undefined, { path: { id: expected.id } })
      if (permission.id !== expected.id || permission.sha256 !== expected.sha256 || permission.size !== expected.size || permission.artifact.sha256 !== expected.sha256 || permission.artifact.size !== expected.size || permission.artifact.artifact_id !== artifact.artifact_id) throw new Error('原件权限或冻结来源在下载期间发生变化，未下载。')
      if (!alive.current || generation !== epoch.current || authGeneration !== getSessionGeneration()) return
      const url = URL.createObjectURL(blob); urls.current.add(url)
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = artifact.filename; anchor.click()
      setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 1000)
    } catch (reason) { if (alive.current && generation === epoch.current) setError((reason as Error).message) } finally { if (alive.current && generation === epoch.current) setBusy(false) }
  }
  const author = async () => {
    setBusy(true); setError('')
    const generation = epoch.current
    try { await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': crypto.randomUUID() }); if (alive.current && generation === epoch.current) refresh() } catch (reason) { if (alive.current && generation === epoch.current) setError((reason as Error).message) } finally { if (alive.current && generation === epoch.current) setBusy(false) }
  }
  return <details className="reader-sources" data-view-key={`sources-${value.block.id}`}>
    <summary data-focus-key={`sources-${value.block.id}`}>来源与提取诊断</summary>
    <p>来源记录不代表内容或数学审校通过。</p>
    {original ? <section className="retained-original"><h3>保留原件</h3><p>{original.source.media_type} · {original.source.size} 字节</p><p>原件 SHA-256：<code>{original.source.sha256}</code></p>
      {original.original_access === 'allowed' ? <button disabled={busy} onClick={() => void download(original.source)}>下载受控原件</button> : original.original_access === 'author_required' ? <p>原件需要作者角色。<button disabled={busy} onClick={() => void author()}>切换为作者以读取原件</button></p> : <p>原件暂不可读取。</p>}
    </section> : <p>没有可读的原件绑定；不会用引用记录猜测下载文件。</p>}
    {value.citations.map(item => <div key={item.citation.id}><strong>{item.citation.title}</strong><p>{sourceLocatorLabel(item.citation.locator)}</p><p>{item.citation.verification === 'user_supplied' ? '用户提供 · 尚未独立核实' : item.citation.verification === 'verified' ? '来源已核实' : '来源未核实'}</p><code>{item.citation.source_sha256 ?? '引用未提供来源哈希'}</code></div>)}
    {value.unresolved_citation_ids.length > 0 && <p>来源尚未解析：{value.unresolved_citation_ids.join('、')}</p>}
    {!value.citations.length && !value.unresolved_citation_ids.length && <p>此块没有提供引用记录。</p>}
    {value.warnings.map((warning, index) => <p key={`${warning.code}:${index}`}>{warning.code} · {warning.message}{warning.locator && <small>{warning.locator}</small>}</p>)}
    {error && <p role="alert">{error}</p>}
  </details>
}
