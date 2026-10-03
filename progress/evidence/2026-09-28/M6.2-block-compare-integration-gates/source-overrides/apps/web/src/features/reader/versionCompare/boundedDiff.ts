export type LineChange = { kind: 'same' | 'removed' | 'added'; text: string }
export type LineComparison = { kind: 'diff'; changes: LineChange[] } | { kind: 'parallel'; reason: string }
/** Linear prefix/suffix line comparison; the changed middle is shown whole, not
 * claimed to be a minimum edit or semantic comparison. UTF-16 length is a
 * conservative work budget; no Unicode normalization or newline trimming. */
export function boundedLineDiff(left: string, right: string): LineComparison {
  const fallback: LineComparison = { kind: 'parallel', reason: '超过差异标记上限（两侧合计 100,000 字符单位或 2,000 行），以下完整原文并列保留。' }
  if (left.length + right.length > 100000) return fallback
  const a = left ? left.split(/(?<=\n)/u) : [], b = right ? right.split(/(?<=\n)/u) : []
  if (a.length + b.length > 2000) return fallback
  let start = 0, end = 0
  while (start < a.length && start < b.length && a[start] === b[start]) start++
  while (end < a.length - start && end < b.length - start && a[a.length - 1 - end] === b[b.length - 1 - end]) end++
  const changes: LineChange[] = [
    { kind: 'same', text: a.slice(0, start).join('') },
    { kind: 'removed', text: a.slice(start, a.length - end).join('') },
    { kind: 'added', text: b.slice(start, b.length - end).join('') },
    { kind: 'same', text: end ? a.slice(a.length - end).join('') : '' },
  ]
  return { kind: 'diff', changes: changes.filter(change => change.text !== '') }
}
