import type { CSSProperties } from 'react'

export type DraftConflictPreviewProps = {
  base: string | null
  local: string
  stored: string
}

const textStyle: CSSProperties = {
  margin: '6px 0 0',
  padding: 8,
  minWidth: 0,
  maxWidth: '100%',
  maxHeight: '12rem',
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
  overflowWrap: 'anywhere',
  font: 'inherit',
  border: '1px solid var(--border-subtle)',
  background: 'var(--bg-surface)',
}

/** Displays the supplied snapshots without resolving or changing a draft. */
export function DraftConflictPreview({ base, local, stored }: DraftConflictPreviewProps) {
  const versions = [
    { label: '原基准', text: base },
    { label: '当前页面', text: local },
    { label: '已存草稿', text: stored },
  ]

  return <section aria-label="问题草稿三方比较" style={{ minWidth: 0, maxWidth: '100%' }}>
    <p style={{ margin: '8px 0', lineHeight: 1.6 }}>选择前请核对各版本；下方仅展示草稿，不会自动合并或覆盖。</p>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))', gap: 8, minWidth: 0 }}>
      {versions.map(({ label, text }) => <div key={label} style={{ minWidth: 0 }}>
        <h4 style={{ margin: 0, fontSize: 'inherit' }}>{label}</h4>
        {text === null
          ? <p style={{ margin: '6px 0', lineHeight: 1.6 }}>原基准未知，无法判断相对原基准的改动。</p>
          : <pre role="region" aria-label={`${label}正文`} tabIndex={0} style={textStyle}>{text === '' ? '（空草稿）' : text}</pre>}
      </div>)}
    </div>
  </section>
}
