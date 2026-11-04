# 报告归一化与风险决策

## 加载与覆盖

从 `evidence/` 读取 `material-check.json`、`attack-surface.json`、`secret-scan.json`、`authz-findings.json`、`payment-findings.json`、`dataflow-analysis.json`、`privacy-compliance.json`、`dynamic-test-results.json`。具体容器见入口的字段映射表。

逐个记录来源文件与读取结果：缺失、解析失败、结构无效、成功。仅成功解析且结构符合约定的空容器表示该输入零记录；缺文件、解析失败、上游未执行或执行失败均为覆盖缺口。文件存在不证明审计已完成，需结合执行记录和材料限制判断。不能用空数组替代读取错误。未知材料元数据写未知，不从目录名推测版本或环境。

## 归一化与去重

领域 `findings[]`、隐私 `sections.<section>.issues[]` 已使用 finding schema，直接保留字段。secret 的 `secrets[]` 是无 severity 的候选，先保留规则、路径、行号和脱敏摘录，再创建 needs_validation 记录并说明 `validation_needed`；不能因字符串像凭证就确认有效性、权限或暴露范围。

以失效边界、根因和受影响控制核对重复项；相同标题、同类规则或同一 URL 不足以合并。不同根因或不同修复措施应分开。合并时保留所有来源、证据引用、位置及相关数据流，不能丢失反证或未知。

已存在的 `finding_id` 是稳定身份；同一 ID 对应不同根因时报告冲突，不静默覆盖。不同 ID 确认重复时选择已有规范记录，记录合并来源 ID 到该记录的映射并更新所有引用。排序只影响显示，禁止按排序生成或重排 ID。首次创建记录才分配下一个未使用的 F-ID。

动态 `findings[]` 是实验记录，按 `finding_id` 关联已有发现。`CONFIRMED` 只提供确认门所需证据；`INCONCLUSIVE` 和 `BLOCKED` 保留原主张、失败原因和缺失事实；`FALSE_POSITIVE` 只有在确实推翻原主张时才支持 rejected。单次失败不证明控制有效，实验没有最终 severity。

## 确认门

- `confirmed`：E2/E3；severity；至少一个可解析的 evidence_refs；root_cause、reproduction、impact、preconditions、retest 为非空文本；remediation 为非空文本数组；verification.method 及 verification.test_case.expected/actual 必须完整且非空。
- `needs_validation`：必须有非空 validation_needed，写明缺失事实与最小验证步骤；禁止 severity，可用 priority。
- `rejected`：必须有非空 rejection_reason，说明否定哪项原主张及依据；禁止 severity，可用 priority。

缺字段的确认主张不能直接发布为 confirmed。补足真实证据，或明确记录降为 needs_validation 的原因并移除 severity；状态缺失的统一领域记录属于输入错误。不得用模板句、猜测或更高证据标签填补内容。

每个证据引用须指向最终 evidence.json 中唯一、真实存在的记录。审查摘录是否证明具体失效、复现是否与预期/实际一致、修复是否落在真正的控制边界。源码定位按已掌握材料填写；HTTP 发现可只有资产与请求证据，不能要求源码行号。dataflow 保留 source/sink/path/transforms/guards、定位与结论不确定性；没有材料时不生成虚构路径。

## 统计与决策

分别统计三种状态；最终风险数量和各 severity 分布只计算 confirmed。待验证条目按 priority 安排补证，不进入风险数量。排除项保留排除依据，避免重新报告同一错误主张。

总体风险是基于证据的解释性判断：说明已证明的损害、权限和可达条件、受影响范围、有效控制及关键未知，并引用 F-ID。不得取最高 severity 标签作为自动总体评级，也不得把候选影响当作事实。当材料不足以支持全局判断时写“总体风险暂无法判断”，同时给出已确认问题的修复决策。零确认发现只说明本次未形成确认结论，不说明目标安全。

## 输出

写 `findings.json`（三种状态的最终记录数组）、`evidence.json`（证据数组）和 `report.md`。用模板组织摘要、确认发现、待验证、排除与覆盖限制；不自动扩展成 API 全量清单、Fuzz 参数导出或无关大文档。显示排序保持 ID 不变，报告统计与 JSON 一致。校验单条 schema 后还需核对数组元素、唯一 ID、引用存在性、合并映射和覆盖结论。
