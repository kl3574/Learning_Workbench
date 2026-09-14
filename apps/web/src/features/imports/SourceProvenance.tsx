import type { Citation } from '../../../../../packages/contracts/generated/types'

const verificationLabels = { verified: '来源已核实；不代表内容审校通过', unverified: '来源尚未核实', user_supplied: '用户提供的参考材料；尚未独立核实' }

export function sourceLocatorLabel(locator: string) {
  const pdf = locator.match(/^source:[^;]+;pdf:page:([1-9]\d*)$/)
  if (pdf) return `PDF 第 ${pdf[1]} 页`
  const docx = locator.match(/^source:[^;]+;docx:part:word\/document\.xml;node:\/w:document\/w:body\/(.+)$/)
  const paragraph = docx?.[1].match(/^w:p\[([1-9]\d*)\]$/)
  if (paragraph) return `DOCX 正文第 ${paragraph[1]} 个段落节点`
  const cell = docx?.[1].match(/^w:tbl\[([1-9]\d*)\]\/w:tr\[([1-9]\d*)\]\/w:tc\[([1-9]\d*)\](?:\/w:p\[([1-9]\d*)\])?$/)
  if (cell) return `DOCX 第 ${cell[1]} 张表 · 第 ${cell[2]} 行 · 第 ${cell[3]} 个单元格${cell[4] ? ` · 第 ${cell[4]} 个段落节点` : ''}`
  return locator
}

export function SourceProvenance({ citations }: { citations: Citation[] }) {
  return <section className="import-provenance" aria-label="当前候选的原件来源">
    <h4>当前候选的原件来源</h4>
    {citations.length ? <ul>{citations.map(citation => <li key={citation.id}>
      <strong>{citation.title}</strong>
      <p className="import-source-locator">原件定位：{sourceLocatorLabel(citation.locator)}</p>
      <p>{verificationLabels[citation.verification]}</p>
      {citation.source_sha256 ? <details><summary>核对该来源的原件 SHA-256</summary><code className="import-hash">{citation.source_sha256}</code></details> : <p className="import-warning">此来源未提供原件哈希，暂时无法核对原件字节。</p>}
      <details><summary>查看精确来源定位</summary><code className="import-hash">{citation.locator}</code></details>
    </li>)}</ul> : <p>服务端尚未提供此候选的精确来源定位；不会按候选顺序推算页码或段落。</p>}
    <p className="muted">请结合本次导入诊断核对原件。页码、段落和表格节点来自提取记录；定位信息不证明版式或公式已准确恢复。</p>
  </section>
}
