export function OperationHelp({ independent, checking = false }: { independent: boolean; checking?: boolean }) {
  return <div className="assessment-operation-help"><h2>Agent · 固定操作帮助</h2><p>{checking ? '正在核验服务端测试策略；尚未向模型提供任何内容。' : independent ? '独立测试进行中。这里仅显示操作说明，不包含题目、作答、笔记或历史学科上下文。' : '本次测试仅允许操作帮助，未调用模型或联网。'}</p><ul><li>用题号目录或 Tab 键移动，作答会自动保存并明确显示状态。</li><li>离线或版本冲突时保留本机候选；重新读取后先比较，再明确恢复。</li><li>提交前确认作答已保存；关闭标签或浏览器不会提交。</li><li>可明确放弃当前测试；放弃不计为独立零分。</li></ul><p>模型：未调用 · 联网：未调用 · 标准答案：未请求</p></div>
}
