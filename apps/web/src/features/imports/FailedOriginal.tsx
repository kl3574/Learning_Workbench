import { useEffect, useRef, useState, type RefObject } from 'react'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'

export function FailedOriginal({ originalFile, expectedHash, accessEpoch, onOriginalFile }: {
  originalFile: File | null; expectedHash: string; accessEpoch: RefObject<number>; onOriginalFile?: (file: File | null) => void;
}) {
  const [file, setFile] = useState(originalFile)
  const [verified, setVerified] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const generation = useRef(0)
  const urls = useRef(new Set<string>())
  useEffect(() => () => {
    generation.current++
    for (const url of urls.current) URL.revokeObjectURL(url)
    urls.current.clear()
  }, [])
  const verify = async () => {
    if (!file) return
    const attempt = ++generation.current
    const epoch = accessEpoch.current
    setVerified(false); setError(''); setBusy(true); setSaved(false)
    try {
      const digest = bytesToHex(sha256(new Uint8Array(await file.arrayBuffer())))
      if (attempt !== generation.current || epoch !== accessEpoch.current) return
      if (digest !== expectedHash) throw new Error('所选文件与失败导入的原件 SHA-256 不一致，未提供原件副本。')
      setVerified(true)
    } catch (reason) { if (attempt === generation.current && epoch === accessEpoch.current) setError(reason instanceof Error ? reason.message : '无法读取本机文件。') }
    finally { if (attempt === generation.current && epoch === accessEpoch.current) setBusy(false) }
  }
  const save = () => {
    if (!verified || !file) return
    try {
      const url = URL.createObjectURL(file)
      urls.current.add(url)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = file.name; anchor.click(); setSaved(true)
      setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 60000)
    } catch { setError('本机副本未能保存，请重试。服务端失败记录未改变。') }
  }
  return <section className="import-notice" aria-label="核对失败导入的本机原件">
    <h3>核对本机原件</h3>
    <p>失败原件及其哈希已在服务端保留，目前暂不能从这里下载。你可以选择本机原件核对哈希，再保存副本，用本机阅读器查看。</p>
    {!originalFile && <p>刷新或关闭后，浏览器不再持有原始文件。请重新选择原件进行哈希核对。</p>}
    {file && <p>本机文件：{file.name} · {file.size} 字节</p>}
    <label className="import-file">选择用于核对的原始文件<input type="file" onChange={event => { generation.current++; setFile(event.target.files?.[0] ?? null); onOriginalFile?.(event.target.files?.[0] ?? null); setVerified(false); setError(''); setBusy(false); setSaved(false) }} /></label>
    <div className="import-buttons"><button type="button" disabled={!file || busy} onClick={() => void verify()}>{busy ? '正在核对原件哈希…' : '核对本机原件 SHA-256'}</button></div>
    {error && <p className="import-error" role="alert">{error}</p>}
    {verified && <><p role="status">本机文件与失败导入的原件哈希一致。本次本机核对未提取正文、未运行 OCR，也未改变导入状态。</p><button type="button" onClick={save}>保存本机原件副本以查看</button><p>保存的是相同原始字节，可用本机阅读器查看。此操作不是服务端下载，浏览器仅复制字节。</p></>}
    {saved && <p role="status">已发起本机原件副本下载；是否可被阅读器打开尚未验证。</p>}
  </section>
}
