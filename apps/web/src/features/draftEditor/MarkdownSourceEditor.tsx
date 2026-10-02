import { useLayoutEffect, useRef } from 'react'
import { Compartment, EditorState } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { markdown } from '@codemirror/lang-markdown'
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language'

type Props = { value: string; onChange: (value: string) => void; sourceIdentity: string; label: string; disabled?: boolean }

/** Source text only. The caller owns identity, permissions and durable saves. */
export function MarkdownSourceEditor({ value, onChange, sourceIdentity, label, disabled = false }: Props) {
  const host = useRef<HTMLDivElement>(null), editor = useRef<EditorView | null>(null)
  const latest = useRef({ value, onChange, sourceIdentity, label, disabled })
  latest.current = { value, onChange, sourceIdentity, label, disabled }
  const sync = useRef<(() => void) | null>(null)

  useLayoutEffect(() => {
    if (!host.current) return
    let alive = true
    const access = new Compartment()
    const accessExtensions = () => [EditorState.readOnly.of(latest.current.disabled), EditorView.editable.of(!latest.current.disabled),
      EditorView.contentAttributes.of({ 'aria-label': latest.current.label, 'aria-multiline': 'true',
        'aria-disabled': String(latest.current.disabled), 'aria-readonly': String(latest.current.disabled),
        role: 'textbox', spellcheck: 'false', autocapitalize: 'off', autocorrect: 'off' })]
    const makeState = (text: string) => EditorState.create({ doc: text, extensions: [
      // Preserve every source codepoint and every LF, including trailing blank
      // lines. Markdown parsing/highlighting never serializes the document.
      EditorState.lineSeparator.of('\n'), markdown({ addKeymap: false }), syntaxHighlighting(defaultHighlightStyle),
      history(), keymap.of([...historyKeymap, ...defaultKeymap]), EditorView.lineWrapping, access.of(accessExtensions()),
      EditorView.updateListener.of(update => {
        if (alive && latest.current.sourceIdentity === sourceIdentity && !latest.current.disabled && update.docChanged)
          latest.current.onChange(update.state.doc.toString())
      }),
    ] })
    const view = new EditorView({ parent: host.current, state: makeState(latest.current.value),
      dispatchTransactions: (transactions, target) => {
        // A fieldset does not disable contenteditable. Also fence a stale view
        // between a new render and effect cleanup, and after destroy().
        if (!alive || latest.current.sourceIdentity !== sourceIdentity ||
            latest.current.disabled && transactions.some(transaction => transaction.docChanged)) return
        target.update(transactions)
      },
    })
    editor.current = view
    let configuration = JSON.stringify([latest.current.disabled, latest.current.label])
    sync.current = () => {
      if (!alive || latest.current.sourceIdentity !== sourceIdentity) return
      const next = JSON.stringify([latest.current.disabled, latest.current.label])
      if (view.state.doc.toString() !== latest.current.value) {
        // An external replacement is a new authoritative document, not a user
        // edit. Drop old undo data; never emit it back through onChange.
        view.setState(makeState(latest.current.value))
        configuration = next
      } else if (next !== configuration) {
        view.dispatch({ effects: access.reconfigure(accessExtensions()) })
        configuration = next
      }
    }
    return () => {
      alive = false; sync.current = null; editor.current = null
      // Release sensitive text and undo state as well as DOM observers/listeners.
      view.setState(EditorState.create()); view.destroy()
    }
  }, [sourceIdentity])

  useLayoutEffect(() => { sync.current?.() }, [value, disabled, label, sourceIdentity])
  return <div className="markdown-source-editor"><div className="markdown-source-label">{label}</div><div ref={host} /></div>
}
