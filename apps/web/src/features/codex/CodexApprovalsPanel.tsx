import { useState } from 'react'
import type { CodexTurnControlView } from '../../../../../packages/contracts/generated/codex-turn-types'
import type { DraftStore } from '../../workbench/DraftStore'
import { approvalClient, type ApprovalPort } from './approvalClient'
export type ApprovalPanelState = { dirty: boolean; safe: boolean; isolated: boolean }
export function CodexApprovalsPanel({ port = approvalClient }: { workspace: string; writeAdmitted: boolean; port?: ApprovalPort; store?: DraftStore; formStore?: DraftStore; onState?: (value: ApprovalPanelState) => void }) {
 const [ready, setReady] = useState(false), [turn, setTurn] = useState(''), [control, setControl] = useState<CodexTurnControlView | null>(null)
 return <section aria-label="Codex 逐操作审批"><button onClick={() => void port.session().then(() => setReady(true))}>读取审批记录与权限</button>
  {ready && <><p>审批本机记录已读取。</p><label>审批来源 turn ID<input value={turn} onChange={e => setTurn(e.target.value)} /></label><button onClick={() => void port.control(turn).then(setControl)}>独立读取审批安全控制</button></>}
  {control && <section aria-label="审批安全控制 GET">{control.approval_controls.map(a => <p key={a.id}>{a.id} · {a.decision}</p>)}</section>}
 </section>
}
