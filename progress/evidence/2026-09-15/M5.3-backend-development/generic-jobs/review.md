# Tutor 通用 Jobs HTTP 修复

范围是当前 m53-active 的通用 GET /jobs/{id} 与 POST /jobs/{id}/cancel。实际 native22 的 GET500由 C 运行；本审计不冒称运行原生浏览器。原 Run cancel 控制 DTO 不变。

HTTP 原相同两case、相同测试文件字节：red-01 2FAIL（两个真实500）→green-02 2PASS0.77s。实际应用与注册的路由/response_model都使用TestClient，没有模拟业务响应，也没有运行lifespan后台任务。H1为response模型与返回ControlView不符；同形修复直接支持H1，不是超时或UI等待修改。

安全快照由Jobs当前完整历史及精确event生成，实际created_at/updated_at/status/revision，固定状态进度；不含正文、refs、warnings、敏感error。Generic cancel使用独立原route/key与完整JobSnapshot ACK；原ACK核原任务完整历史、真实event与原取消条件/记录时间，再回原版本与时间。

新增合法terminal no-op后同key回放曾被初版错误判为transition：terminal-noop-red-03实际1FAIL409，修后http-final-05同一case正文PASS。green-04实际34PASS1FAIL，失败是新增missing_user测试误用tutor_messages.id，非产品损坏反例；修成messages.id/tutor_messages.message_id后final-05实际35PASS14.96s（新9+原HTTP6+原Runs20）。

负控包含真实running lease保留、旧ACK在最终terminal后仍原时间/版本、stale terminal no-op、generic/run两route同key独立、同key改body拒绝、当前independent/open_book控制仍安全可读、将ACK自洽替换成后来实际snapshot/敏感progress/删除原user历史均拒绝且零新写。

Lint-06仅新测试fixture导入F811，改导入别名及显式yield原fixture后lint-final-08通过，最终同9case fixture-final-09通过3.56s；types-07三个生产文件通过。没有扩大原断言或timeout。所有列出输入的各run前后均相同，不代表整仓固定验收。

无浏览器、无用户密钥、无paid或外部Provider调用。本次原Tests中的本地受控HTTP协议仅保留其原范围。C接手原三native、root接手完整门禁。本目录不含数据库/秘密文件。
