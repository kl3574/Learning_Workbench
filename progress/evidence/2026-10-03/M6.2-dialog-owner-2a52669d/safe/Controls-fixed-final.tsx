import { useEffect, useRef, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'
import { resizeValue } from './model'
export function Dialog({ title, children, close, className = '' }: { title: string; children: ReactNode; close: () => void; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null)
  // A content press can finish as a click on the dialog after movement or layout
  // changes. Only a complete primary gesture outside its box requests closing.
  const backdropPress = useRef<{ id: number; released: boolean } | null>(null)
  const onBackdrop = (event: ReactPointerEvent<HTMLDialogElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return event.target === event.currentTarget && (event.clientX < rect.left || event.clientX >= rect.right || event.clientY < rect.top || event.clientY >= rect.bottom)
  }
  useEffect(() => { const dialog = ref.current; const opener = document.activeElement as HTMLElement | null; dialog?.showModal(); dialog?.querySelector<HTMLElement>('button')?.focus(); return () => { dialog?.close(); opener?.focus() } }, [])
  return <dialog ref={ref} className={className} aria-label={title}
    onPointerDownCapture={event => { backdropPress.current = event.isPrimary && event.button === 0 && onBackdrop(event) ? { id: event.pointerId, released: false } : null }}
    onPointerUpCapture={event => { const press = backdropPress.current; if (press?.id === event.pointerId && event.isPrimary && event.button === 0 && onBackdrop(event)) press.released = true; else backdropPress.current = null }}
    onPointerCancelCapture={() => { backdropPress.current = null }}
    onKeyDown={event => { if (event.key !== "Tab") return; const items = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"],summary')).filter(item => item.getClientRects().length > 0); const first = items[0]; const last = items.at(-1); if ((event.shiftKey && document.activeElement === first) || (!event.shiftKey && document.activeElement === last)) { event.preventDefault(); (event.shiftKey ? last : first)?.focus() } }} onCancel={event => { event.preventDefault(); backdropPress.current = null; close() }} onClick={event => { const press = backdropPress.current; backdropPress.current = null; if (press?.released && event.target === event.currentTarget) close() }}><div className="dialog-inner"><header><h2>{title}</h2><button autoFocus onClick={close} aria-label={`关闭${title}`}>×</button></header>{children}</div></dialog>
}
export function Splitter({ side, value, otherWidth, collapsed, onResize, toggle }: { side: 'nav' | 'agent'; value: number; otherWidth: number; collapsed: boolean; onResize: (value: number) => void; toggle: () => void }) {
  const min = side === 'nav' ? 260 : 320
  const max = side === 'nav' ? 360 : 480
  return <div className="splitter" role="separator" tabIndex={0} aria-label={side === 'nav' ? '导航栏宽度' : 'Agent 栏宽度'} aria-orientation="vertical" aria-controls={`${side}-pane`} aria-valuenow={collapsed ? 0 : value} aria-valuemin={0} aria-valuemax={max} aria-valuetext={collapsed ? '已折叠，Enter 恢复' : `${value} 像素；展开范围 ${min} 至 ${max}`} onKeyDown={event => {
    let next: number | undefined
    if (event.key === 'Enter') { event.preventDefault(); toggle(); return }
    if (event.key === 'Home') next = min
    if (event.key === 'End') next = max
    if (event.key === 'ArrowLeft') next = value + (side === 'nav' ? -16 : 16)
    if (event.key === 'ArrowRight') next = value + (side === 'nav' ? 16 : -16)
    if (next !== undefined) { event.preventDefault(); if (collapsed) toggle(); onResize(resizeValue(side, next, innerWidth, otherWidth)) }
  }} onPointerDown={event => {
    if (collapsed) return
    event.currentTarget.setPointerCapture(event.pointerId)
    const start = event.clientX; const initial = value; const target = event.currentTarget
    const move = (moveEvent: PointerEvent) => onResize(resizeValue(side, initial + (moveEvent.clientX - start) * (side === 'nav' ? 1 : -1), innerWidth, otherWidth))
    const finish = () => { target.removeEventListener('pointermove', move); target.removeEventListener('pointerup', finish); target.removeEventListener('pointercancel', finish) }
    target.addEventListener('pointermove', move); target.addEventListener('pointerup', finish); target.addEventListener('pointercancel', finish)
  }} />
}
