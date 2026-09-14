import { findLesson, fixture, sameRef } from '../features/fixture'
import { navigationItems, type Session } from './model'
const rows: { title: string; value: (session: Session) => string }[] = [
  { title: '课程', value: s => !s.course_ref ? '未选择课程' : sameRef(s.course_ref, fixture.course.ref) ? '合成示例课程' : '保留的课程引用（待解析）' },
  { title: '当前入口', value: s => navigationItems.find(item => item.id === s.navigation)?.label ?? '未知入口' },
  { title: '导航栏', value: s => s.nav_collapsed ? '已折叠' : `展开，${s.nav_width} 像素` },
  { title: 'Agent 栏', value: s => s.agent_collapsed ? '已折叠' : `展开，${s.agent_width} 像素` },
  { title: '打开的内容', value: s => s.tabs.length ? s.tabs.map(tab => `${findLesson(tab.context.active_ref)?.title ?? '待解析对象'} · 修订 ${tab.context.active_ref.revision}${tab.id === s.active_tab_id ? '（当前）' : ''}`).join('；') : '没有打开的内容' },
  { title: '目录位置', value: s => `距顶部 ${Math.round(s.directory_scroll)} 像素，展开 ${s.expanded_keys.length} 项` },
  { title: '阅读位置', value: s => { const tab = s.tabs.find(item => item.id === s.active_tab_id); return tab ? `距顶部 ${Math.round(tab.scroll_offset ?? 0)} 像素` : '没有当前内容' } },
]
export function ConflictComparison({ comparison, retainLocal, useServer }: { comparison: { base: Session | null; local: Session; remote: Session | null }; retainLocal: () => void; useServer: () => void }) {
  return <section className="conflict-comparison" aria-label="会话三方比较"><details open><summary>比较会话版本并明确选择</summary><p>原基准是编辑开始时已确认的会话。本地一栏包含尚未确认的修改；采用任一版本都保留问题草稿。</p><div className="comparison-scroll"><table><thead><tr><th>项目</th><th>原基准{comparison.base ? `（版本 ${comparison.base.revision}）` : '（未知）'}</th><th>本地待同步</th><th>服务端{comparison.remote ? `（版本 ${comparison.remote.revision}）` : '（未知）'}</th></tr></thead><tbody>{rows.map(row => <tr key={row.title}><th scope="row">{row.title}</th><td>{comparison.base ? row.value(comparison.base) : '未保存该基准，无法比较'}</td><td>{row.value(comparison.local)}</td><td>{comparison.remote ? row.value(comparison.remote) : '尚未读取，不能推测'}</td></tr>)}</tbody></table></div><div className="comparison-actions"><button disabled={!comparison.remote} onClick={retainLocal}>采用本地会话并重新保存</button><button onClick={useServer}>采用服务端会话，放弃本地 UI 修改</button></div></details></section>
}
