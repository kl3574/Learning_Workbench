import { useState } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Dialog } from './Controls'

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute('open') } })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal'); Reflect.deleteProperty(HTMLDialogElement.prototype, 'close') })

function Example() {
  const [open, setOpen] = useState(true)
  return open && <Dialog title="Pointer example" close={() => setOpen(false)}><button>Read details</button></Dialog>
}

it('keeps the dialog when a content press ends with a click retargeted to its backdrop', () => {
  render(<Example />)
  const dialog = screen.getByRole('dialog'), button = screen.getByRole('button', { name: 'Read details' })
  fireEvent.pointerDown(button, { pointerId: 1, isPrimary: true, button: 0 })
  fireEvent.pointerUp(dialog, { pointerId: 1, isPrimary: true, button: 0 })
  fireEvent.click(dialog)
  expect(screen.queryByRole('dialog')).toBe(dialog)
})

const outside = { pointerId: 1, isPrimary: true, button: 0, clientX: 2, clientY: 2 }
function example() {
  render(<Example />)
  const dialog = screen.getByRole('dialog'), button = screen.getByRole('button', { name: 'Read details' })
  vi.spyOn(dialog, 'getBoundingClientRect').mockReturnValue(DOMRect.fromRect({ x: 100, y: 100, width: 400, height: 300 }))
  return { dialog, button }
}

it('closes for a primary press and release both on the backdrop', () => {
  const { dialog } = example()
  fireEvent.pointerDown(dialog, outside); fireEvent.pointerUp(dialog, outside); fireEvent.click(dialog)
  expect(screen.queryByRole('dialog')).toBeNull()
})

it.each(['released on content', 'captured release inside box', 'different pointer', 'cancelled', 'secondary', 'no press', 'dialog interior'] as const)('keeps the dialog for %s', mode => {
  const { dialog, button } = example()
  const start = mode === 'secondary' ? { ...outside, button: 2 } : mode === 'dialog interior' ? { ...outside, clientX: 120, clientY: 120 } : outside
  if (mode !== 'no press') fireEvent.pointerDown(dialog, start)
  if (mode === 'cancelled') fireEvent.pointerCancel(dialog, outside)
  fireEvent.pointerUp(mode === 'released on content' ? button : dialog,
    mode === 'captured release inside box' ? { ...outside, clientX: 120, clientY: 120 } : mode === 'different pointer' ? { ...outside, pointerId: 2 } : outside)
  fireEvent.click(dialog)
  expect(screen.queryByRole('dialog')).toBe(dialog)
})

it('consumes a background gesture once even when the caller retains an unsaved dialog', () => {
  const close = vi.fn()
  render(<Dialog title="Guarded example" close={close}><p>Unsaved text remains with the caller.</p></Dialog>)
  const dialog = screen.getByRole('dialog')
  fireEvent.pointerDown(dialog, outside); fireEvent.pointerUp(dialog, outside); fireEvent.click(dialog)
  expect(close).toHaveBeenCalledTimes(1)
  fireEvent.click(dialog)
  expect(close).toHaveBeenCalledTimes(1)
  expect(screen.getByText('Unsaved text remains with the caller.')).toBeTruthy()
})

it.each(['close button', 'Escape cancellation'] as const)('preserves %s through the caller close guard', mode => {
  const close = vi.fn()
  render(<Dialog title="Guarded example" close={close}><p>Unsaved text remains with the caller.</p></Dialog>)
  const dialog = screen.getByRole('dialog')
  if (mode === 'close button') fireEvent.click(screen.getByRole('button', { name: '关闭Guarded example' }))
  else expect(fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))).toBe(false)
  expect(close).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('dialog')).toBe(dialog)
})
