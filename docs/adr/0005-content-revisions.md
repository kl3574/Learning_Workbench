# ADR 0005 — M2.1 内容修订读取与存储接口

日期：2026-09-14。唯一规范为根目录 PRODUCT_DESIGN.md 3.0.0，引用第 9、20.1、20.2 节及附录 A/B/C。本记录说明实现选择；实际验证状态见 progress/state.json。

内容 API 与本机 UI 会话 API 使用独立 router，分别声明可接受的查询字段，拒绝未知或重复查询。课程、小节、块均要求明确整数 revision；不存在的修订不回退到 latest。metadata 响应使用固定模型规范 JSON 的 SHA-256 作为 ETag，Markdown 使用原始正文 SHA-256；正文另走 text/markdown，不经过重新排版或序列化。current 只解析指针，后续操作仍固定具体 ContentRef。

新增内容读取只有七条已声明的接口：课程列表、课程、小节、块、块正文、当前引用和修订列表。课程摘要及修订列表使用严格 DTO；存储状态 published 不代表内容审校，当前未审材料明确返回 unreviewed。目录/笔记/导入接口在所属任务实现，不注册成功占位。

内嵌 ContentBlock 的交换字段继续使用 citations 和 concepts；它们分别承担正文中来源引用、概念 ID 的语义。后续导入在 Citation/source 记录中绑定原件 hash，不增加另一份可独立修改的正文，也不把可读正文推定为来源已核验。原始规范保持字节不变。

生成客户端对 path/query 做类型化绑定及 URL 编码，对 text/markdown 显式采用 text transport。已有 UI 会话调用形式保持兼容；未实现的 multipart/其他 MIME 继续明确拒绝。HTTP 层只做参数和结果投影，内容权限、独立测试 guard、精确修订和存储事务由应用服务负责。

内容写入目前是内部应用端口，为下一任务的导入确认流程提供事务边界；本阶段没有公开发布或导入成功接口。blob 物理路径遵循备份约定 blobs/<hash前两位>/<hash>，交换文档 body_path 只作为载荷映射键，不作为本机任意路径。文件先落盘，后建立数据库引用；失败结果和未引用文件的处理按规范记录，不伪造完成状态。

新候选的纯概念 ID 在发布事务内解析为同批或当前精确修订，随后记录到 object_dependencies。再次使用旧修订时必须读取这份冻结依赖，不重新解析 current；一个课程不能静默混合同一概念的两个修订。Linux blob 使用不覆盖目标的原子 rename 和文件、目录 fsync，持久化失败不会提交数据库引用；没有安全原子能力时明确返回错误。
