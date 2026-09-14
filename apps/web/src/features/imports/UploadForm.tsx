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
  const unsupported = !!file && /\.(pdf|docx)$/i.test(file.name)
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (file && !unsupported && !disabled) void submit(file, kind, courseId)
  }
  return <form onSubmit={onSubmit}>
    <p>上传后先检查候选正文与警告，再确认入库。原件与候选会保留在本机工作区。</p>
    <div className="import-fields">
      <label className="import-file">选择导入文件<input type="file" disabled={disabled} accept=".md,.markdown,.txt,.html,.htm,.zip" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>解析格式<select disabled={disabled} value={kind} onChange={event => setKind(event.target.value as ImportKind)}>
        <option value="auto">自动识别</option><option value="markdown">Markdown</option><option value="text">UTF-8 文本</option><option value="html">HTML</option><option value="learnpack">学习包（.learnpack.zip）</option>
        <option value="pdf" disabled>PDF · 尚未支持</option><option value="docx" disabled>DOCX · 尚未支持</option>
      </select></label>
      <label>导入目标<select disabled={disabled} value={courseId} onChange={event => setCourseId(event.target.value)}><option value="">创建新课程</option>{courses.map(course => <option key={course.ref.id} value={course.ref.id}>{course.title} · r{course.ref.revision}</option>)}</select></label>
    </div>
    {moreCourses && <button type="button" onClick={onMoreCourses} disabled={disabled}>载入更多目标课程</button>}
    <p className="muted">目前支持 Markdown、UTF-8 文本、安全 HTML 和学习包。PDF / DOCX 将在后续阶段提供；默认单原件 50 MiB，实际按本机配置校验。</p>
    {file && <p>已选择：{file.name} · {(file.size / 1024).toFixed(1)} KiB</p>}
    {exceedsDefault && <p className="import-warning" role="status">文件超过默认的 50 MiB。上传后由服务端按本机实际配置校验；超限会明确拒绝。</p>}
    {unsupported && <p className="import-error" role="alert">当前阶段尚不支持 PDF / DOCX，未上传。</p>}
    <div className="import-buttons"><button type="submit" className="primary-button" disabled={disabled || !file || unsupported}>上传并生成预览</button></div>
  </form>
}
