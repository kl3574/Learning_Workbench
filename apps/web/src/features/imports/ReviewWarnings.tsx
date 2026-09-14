import type { Warning } from '../../../../../packages/contracts/generated/types'

export function ReviewWarnings({ warnings, accepted, change, disabled }: {
  warnings: Warning[]; accepted: string[]; change: (codes: string[]) => void; disabled: boolean;
}) {
  if (!warnings.length) return <p>服务端未报告导入警告。内容仍未经过数学或来源审校。</p>
  return <section aria-label="导入警告"><h3>逐项核对导入警告</h3><ul className="import-warnings">{warnings.map((warning, index) => <li key={`${warning.code}:${warning.locator}:${index}`} className={warning.severity === 'error' ? 'import-error' : ''}>
    {warning.severity === 'warning' ? <label><input type="checkbox" disabled={disabled} checked={accepted.includes(warning.code)} onChange={event => change(event.target.checked ? [...new Set([...accepted, warning.code])] : accepted.filter(code => code !== warning.code))} /><span>接受警告 <code>{warning.code}</code><br />{warning.message}{warning.locator && <small> · {warning.locator}</small>}</span></label> : <><strong>{warning.severity === 'error' ? '阻塞错误' : '提示'} · <code>{warning.code}</code></strong><p>{warning.message}{warning.locator && <small> · {warning.locator}</small>}</p>{warning.severity === 'error' && <p>此错误不能通过接受警告绕过；请修正原件后重新导入。</p>}</>}
  </li>)}</ul></section>
}
