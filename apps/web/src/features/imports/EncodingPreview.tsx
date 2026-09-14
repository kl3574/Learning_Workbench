import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import { decodeOriginal, encodingChoices, utf8Derivative, type TextEncoding } from './encoding'

export function EncodingPreview({ originalFile, expectedHash, accessEpoch }: {
  originalFile: File | null; expectedHash: string; accessEpoch: RefObject<number>;
}) {
  const [file, setFile] = useState(originalFile)
  const [encoding, setEncoding] = useState<TextEncoding>('utf-8')
  const [preview, setPreview] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [downloaded, setDownloaded] = useState(false)
  const generation = useRef(0)
  const urls = useRef(new Set<string>())
  const derivative = useMemo(() => preview !== null && file ? utf8Derivative(preview, file.name) : null, [preview, file])
  useEffect(() => () => {
    generation.current++
    for (const url of urls.current) URL.revokeObjectURL(url)
    urls.current.clear()
  }, [])
  const reset = () => { generation.current++; setPreview(null); setConfirmed(false); setError(''); setDownloaded(false); setBusy(false) }
  const decode = async () => {
    if (!file) return
    reset(); setBusy(true)
    const attempt = generation.current
    const epoch = accessEpoch.current
    try {
      const bytes = new Uint8Array(await file.arrayBuffer())
      if (generation.current !== attempt || epoch !== accessEpoch.current) return
      setPreview(decodeOriginal(bytes, expectedHash, encoding))
    } catch (reason) {
      if (generation.current === attempt && epoch === accessEpoch.current) setError(reason instanceof Error ? reason.message : '无法读取本机原件，请重新选择。')
    } finally { if (generation.current === attempt && epoch === accessEpoch.current) setBusy(false) }
  }
  const download = () => {
    if (!derivative || !confirmed) return
    try {
      const url = URL.createObjectURL(new Blob([derivative.bytes], { type: 'text/plain;charset=utf-8' }))
      urls.current.add(url)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = derivative.filename; anchor.click()
      setDownloaded(true)
      setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 60000)
    } catch { setError('未能生成下载文件，请重试。原件和失败导入记录保持不变。') }
  }
  return <section className="import-encoding" aria-label="编码选择预览">
    <h3>选择原件编码并在本机预览</h3>
    <p>此操作只在本机浏览器读取你选择的文件，不发送正文、不自动上传。失败导入和原件保持不变；下面的文本仍未导入。</p>
    {!originalFile && <p className="import-warning">刷新或关闭后，浏览器不再持有原文件。请重新选择同一原始文件；只有 SHA-256 与失败记录一致才可预览。</p>}
    {file && <p>本机原始文件：{file.name}</p>}
    <div className="import-fields">
      <label className="import-file">重新选择原始文件<input type="file" accept=".md,.markdown,.txt,.html,.htm" onChange={event => { reset(); setFile(event.target.files?.[0] ?? null) }} /></label>
      <label>原件文本编码<select value={encoding} disabled={busy} onChange={event => { reset(); setEncoding(event.target.value as TextEncoding) }}>{encodingChoices.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    </div>
    <button type="button" disabled={!file || busy} onClick={() => void decode()}>{busy ? '正在本机严格解码…' : '严格解码并预览'}</button>
    {error && <p className="import-error" role="alert">{error}</p>}
    {preview !== null && derivative && <>
      <p role="status">本机编码预览 · 尚未导入。请核对文字，解码成功不等于编码选择正确。</p>
      <pre className="import-encoding-text" tabIndex={0} aria-label="本机解码文本预览">{preview}</pre>
      <dl className="import-details"><dt>UTF-8 派生文件名</dt><dd>{derivative.filename}</dd><dt>派生文件 SHA-256</dt><dd><code className="import-hash">{derivative.sha256}</code></dd></dl>
      <p>派生文件按所选编码解码后重新编码为 UTF-8，与原件分别校验；它不是原始文件。下载后请关闭此任务，再选择派生文件新建导入并核对服务端预览。</p>
      <label className="import-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /><span>我已核对本机解码文本，确认下载 UTF-8 派生文件。</span></label>
      <button type="button" disabled={!confirmed} onClick={download}>下载 UTF-8 派生文件</button>
      {downloaded && <p role="status">已发起派生文件下载，尚未重新导入。原件与失败任务未被修改。</p>}
    </>}
  </section>
}
