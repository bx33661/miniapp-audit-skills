# 可选：Blackboard 证据台账

Blackboard 是可选的外置记忆，不是审计流程引擎。长任务、可能被压缩、需要交接或并行 Agent 时使用；一次性短审计可以不用。

## 适用

- 审计跨多个会话或阶段，上下文可能丢失。
- 需要保留“证据到假设”的关系，而不只是最终结论。
- 多个 Agent 分别做 recon、static、dynamic、report，需要共享现场。
- 阶段结束、暂停或交接前需要检查点。

## 不适用

- 一次性只读检查，几分钟完成。
- 环境没有 blackboard CLI，且用户不想安装。
- 只需要最终报告，不需要保留推理链。

## 映射

| 审计对象 | blackboard | 规则 |
|---|---|---|
| 目标 | `goal` | 标题带包名和版本；detail 写源码路径、appid、范围 |
| 观察/证据 | `fact` / `result` | 只写实际观察；`--at` 写文件:行；`--status confirmed` 仅用于已观察事实 |
| 假设/漏洞 | `vuln` / `finding` | severity 与 confidence 分开；未验证用 `suspected`；静态核对后用 `static-confirmed`；真实复现后才用 `reproduced` |
| 证据支持 | `supports` 边 | 证据指向假设 |
| 证据反驳 | `contradicts` 边 | 证据指向旧假设，并将旧假设标为 `refuted` |
| 阶段结束 | `checkpoint` | 写已确认、当前节点、开放问题和限制 |
| 交接/压缩 | `checkpoint` / `context` | 用 `context` 恢复，不把投影当成行动指令 |

## 最小用法

使用 blackboard Skill 的 CLI；以下只说明审计语义，不重复安装和配置。

```sh
blackboard init --title "审计 包名@版本" --cwd "/项目根"
blackboard goal "审计 包名@版本" --detail "源码路径、appid、范围" --enter --cwd "/项目根" --no-init
blackboard vuln "候选结论" --sev high --confidence suspected --to "<目标ID>" --cwd "/项目根" --no-init
blackboard fact "实际观察到的证据" --at "file:line" --to "<候选ID>" --rel supports --cwd "/项目根" --no-init
blackboard checkpoint --summary "已确认；当前节点；开放问题；限制" --cwd "/项目根" --no-init
```

每条写命令带 `--cwd` 和 `--no-init`；并行时加 `--agent recon|static|dynamic|report`。

## 边界

- 黑板失败不阻断审计；它不是批准、排序或下一步的决策者。
- 黑板不是报告源；最终报告仍按 `finding.schema.json` 归一化。
- 报告状态 `confirmed` / `needs_validation` / `rejected` 由 report 技能决定；blackboard 的 confidence 只表示证据成熟度，不是报告状态。
- 不把完整密钥、Token 或个人信息写入黑板；写位置、哈希和脱敏摘要。
- `status`、`severity`、`confidence` 缺省为 null，不等于 open 或已确认。
- 黑板数据可能包含敏感摘要；保留在本地，交付前审查。

## 与阶段的关系

- recon：记录材料、版本、缺失项和覆盖限制。
- threat model：记录目标、关键假设和开放问题。
- static：记录证据和假设，不把模式写成 confirmed。
- dynamic：记录结果；只有真实复现才升级为 `reproduced`。
- report：可从黑板导出候选作为输入，但最终字段以报告 schema 为准。
