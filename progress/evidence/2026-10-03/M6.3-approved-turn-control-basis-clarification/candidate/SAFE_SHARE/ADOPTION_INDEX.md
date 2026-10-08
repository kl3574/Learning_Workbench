## 11. v3.0.15 采纳索引与原发现保留

本文件第2–10节是可纳入唯一规范的新完整合同正文；第1节记录相对 v3.0.14 的来源/差异，第11节仅供机械采纳与追踪，不代替根规范。建议新增 §20.17 并按下表交叉引用，旧字节合同只作所列精确修订，不重写54 core/0001。

| v3.0.14 原位置 | 精确采纳动作 |
|---|---|
| 版本表第39行后 | 新增 v3.0.15，记录受批 turn/逐操作审批/产物回导及安全减权基准；状态仍待真实实施验收，不标整个M6.3/AC-21完成 |
| §20.16 第1372、1421–1426、1435、1463、1467–1469、1473、1486行；A 第2322行 | 保留 bootstrap 空actions、原准备/决定/create ACK和原冻结记录；将“当前session GET恒null/flagsfalse/r1-r2”的范围明确限为尚无新turn控制历史的对象，并引用本文第4节当前投影规则；原create ACK仍r2/flagsfalse，本地bootstrap许可绝不授权新turn，bootstrap原actor/期限规则不变 |
| §20.5 第1021–1068行；A 第1956–1967、2048行 | 原M5.1普通Provider预算/wire/历史不变；增加指向本文第2、3节Codex独立具名summary/许可的限定例外；每次模型仍一次请求、完整InputProof、真实独立许可，工具额度不作外发许可 |
| A 第2069行 | 通用审批决定响应由未实现的粗RunSnapshot细化为GenericApprovalDecisionAck；增加本文第5节完整只读view；现有ApprovalDecision原字段不变；减权basis来自本文第4节现有安全turn GET，不另加路由 |
| A 第2074行 | 尚未注册的message/refs直接turn发送形状替换为CodexTurnStartWrite；增加本文第3节prepare及Codex许可八行操作表，保留原turn开始路由 |
| A 第2075行 | interrupt原请求/响应字段不变，补本文第6节一次控制、CAS、失权与未知不重启语义 |
| A 第2076行 | artifacts/import原三请求字段及202 JobRef不变，补本文第7节manifest GET、聚合回导GET、严格清单/实际字节/Import归属；不套用核心learnpack Manifest |
| A Codex配套读取表第2319–2322行 | 加入本文第4节turn列表、控制、结果、事件四个GET与闭合DTO；安全控制包含approval_controls/consent_control，fullapproval/fullconsent继续author学科权限 |
| D 第3049–3054行及Provider受检端口第3176–3182行 | 保留粗兼容端口但禁止绕过新合同；新增本文第8节具名owner应用协作及Codex受检输入/许可适配，不修改普通Provider/core类型 |
| F AC-21 第3519–3522行及M6.3第957行 | 原目标不删除、不降级；增加本文第10节验收矩阵与单次模型上限/真实proof门禁说明，受控协议PASS与真正CLI/model/工具事实分列 |

原 `4e8d4f79` 及原作者收据保持不变。后续独审确认的P2分别为：安全control只有approval_ids，无法构造必填operation_sha256/expected_revision的decline；fullconsent包含学科summary，受限用户无法发现并取得revoke所需许可id/revision。第4节两项闭合安全投影、强成员关联及第10节回归要求闭合这些同范围缺口。它们不追认原版本已可完成减权，也不以合同澄清冒充产品测试通过。
