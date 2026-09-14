import { useState, type FormEvent } from 'react'
import type { CoursePage, ImportKind } from './contracts'

export function UploadForm({ disabled, courses, moreCourses, onMoreCourses, submit }: {
  disabled: boolean; courses: CoursePage['items']; moreCourses: boolean;
  onMoreCourses: () => void; submit: (file: File, kind: ImportKind, courseId: string) => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null)
  const [kind, setKind] = useState<ImportKind>('auto')
  const [courseId, setCourseId] = useState('')
  const exceedsDefault = !!file && file.size > 50 * 1024 * 1024
  const documentKind = kind === 'pdf' || kind === 'docx' ? kind : kind === 'auto' && file ? file.name.match(/\.(pdf|docx)$/i)?.[1].toLowerCase() : null
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (file && !disabled) void submit(file, kind, courseId)
  }
  return <form onSubmit={onSubmit}>
    <p>上传后先检查候选正文与警告，再确认入库。原件与候选会保留在本机工作区。</p>
    <div className="import-fields">
      <label className="import-file">选择导入文件<input type="file" disabled={disabled} accept=".md,.markdown,.txt,.html,.htm,.zip,.pdf,.docx" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>解析格式<select disabled={disabled} value={kind} onChange={event => setKind(event.target.value as ImportKind)}>
        <option value="auto">自动识别</option><option value="markdown">Markdown</option><option value="text">UTF-8 文本</option><option value="html">HTML</option><option value="learnpack">学习包（.learnpack.zip）</option>
        <option value="pdf">PDF · 文本提取</option><option value="docx">DOCX · 段落与表格</option>
      </select></label>
      <label>导入目标<select disabled={disabled} value={courseId} onChange={event => setCourseId(event.target.value)}><option value="">创建新课程</option>{courses.map(course => <option key={course.ref.id} value={course.ref.id}>{course.title} · r{course.ref.revision}</option>)}</select></label>
    </div>
    {moreCourses && <button type="button" onClick={onMoreCourses} disabled={disabled}>载入更多目标课程</button>}
    <p className="muted">支持 Markdown、UTF-8 文本、安全 HTML、学习包及 PDF / DOCX 文本提取；默认单原件 50 MiB，实际按本机配置校验。</p>
    {documentKind === 'pdf' && <p className="import-warning">PDF 仅提取文本层与原件页码，默认不运行 OCR。双栏、表格顺序及图片公式需核对原件；不会自动恢复数学 TeX。</p>}
    {documentKind === 'docx' && <p className="import-warning">DOCX 提取标题、段落和表格，定位到实际文档节点。OMML、浮动图片和复杂版式可能无法保真，不会据此猜造 TeX。安全正文可预览；原件需作者角色读取。</p>}
    {file && <p>已选择：{file.name} · {(file.size / 1024).toFixed(1)} KiB</p>}
    {exceedsDefault && <p className="import-warning" role="status">文件超过默认的 50 MiB。上传后由服务端按本机实际配置校验；超限会明确拒绝。</p>}
    <div className="import-buttons"><button type="submit" className="primary-button" disabled={disabled || !file}>上传并生成预览</button></div>
  </form>
}
