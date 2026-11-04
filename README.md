# MiniApp Audit Skills

面向 Agent 的微信小程序安全审计技能集。支持从运行流量、源码或已有证据独立开始；解包是按需补充材料的能力。

## 工作方式

- 先理解页面、组件、分包、登录、请求封装和可信服务之间的关系，再选择检查方法。
- 只有运行中的小程序与授权账号时，直接进行代理抓包、真实请求重放和多身份测试，无需 wxapkg 或静态发现。
- 有代码时追踪实际路径和安全控制；没有后端实现时不编造服务端缺失校验。
- 线索、待验证、确认与排除分开；确认必须有足够证据，严重性只反映已证明影响。
- 未执行、无法解析、缺材料和测试受阻都保留限制，不解释为安全或零发现。

## 技能

| Skill | 独立用途 | 主要产出 |
|---|---|---|
| miniapp-audit | 确定范围、选择入口、维护证据与覆盖要求 | 会话、范围和覆盖记录 |
| miniapp-recon | 核实已有材料，按需获取或解包 | 声明结构、来源与未知项 |
| miniapp-threat-model | 建模角色、资产、业务状态和边界 | 滥用用例与验证计划 |
| miniapp-static-audit | 审查实际代码、配置和调用路径 | 假设、直接证据和测试思路 |
| miniapp-dynamic | 从流量开始，或验证已有请求/假设 | 实际捕获、重放与对照结果 |
| miniapp-report | 整理任何来源的审计证据与复测标准 | 稳定发现、证据和覆盖说明 |

这些阶段按任务组合，不要求每次串行执行。理解运行结构时读 [runtime-model.md](skills/miniapp-audit/references/runtime-model.md)，身份、渲染、分包和工具疑点按 [平台案例](skills/miniapp-audit/references/platform-cases.md) 定位；独立抓包流程见 [traffic-testing.md](skills/miniapp-dynamic/references/traffic-testing.md)。

## 安装

推荐使用 skills CLI，并安装整套六个技能以保留共享 reference：

```bash
npx skills add bx33661/miniapp-audit-skills
```

Claude Code 插件市场：

```text
/plugin marketplace add bx33661/miniapp-audit-skills
/plugin install miniapp-audit@miniapp-audit-skills
```

手动安装时，在仓库根目录将六个技能目录复制到客户端技能根目录：

```bash
# 项目级 Claude Code
mkdir -p .claude/skills
cp -R skills/miniapp-* .claude/skills/

# 跨客户端约定
mkdir -p .agents/skills
cp -R skills/miniapp-* .agents/skills/
```

复制技能目录本身，不额外包一层命名空间。用户级 Claude Code 可使用 ~/.claude/skills。技能会以 Agent 权限工作，安装前应审阅入口、引用与脚本。

## 使用示例

```text
使用 miniapp-dynamic 对这个运行中的小程序抓包并实际重放请求；我有授权测试账号，没有源码。
使用 miniapp-dynamic 验证这条请求的对象归属，使用两个授权测试账号。
使用 miniapp-static-audit 审查这份源码中的登录、支付和云函数调用。
使用 miniapp-recon 核实这份 wxapkg 材料的主包、分包和插件。
使用 miniapp-report 整理已有证据，保留未验证项和覆盖限制。
使用 miniapp-audit 规划完整审计，并根据现有材料选择入口。
```

导出 curl 或创建请求标签只是准备。动态技能要求实际发送、读取响应并保存证据，分别说明捕获、重放、安全对照和阻塞的完成情况。没有提供目标或运行条件时不能编造流量。

## 实际请求执行

内置执行器按显式计划发送 HTTP/1.1 请求，支持 HTTP/HTTPS、显式 HTTP 代理与 HTTPS CONNECT、受信 CA、隔离账号和 CookieJar。用 [双账号计划示例](skills/miniapp-dynamic/assets/replay-plan-example.json) 组织正常基线与跨对象对照；凭证从指定环境变量读取，不能把示例当作目标协议。

```bash
python3 -m pip install -r skills/miniapp-dynamic/requirements.txt
python3 skills/miniapp-dynamic/scripts/replay.py --plan /path/to/plan.json --output-dir /path/to/new-evidence
python3 scripts/validate_outputs.py --evidence-dir /path/to/new-evidence --verify-artifacts
```

已知协议可使用明确规范的 HMAC-SHA256 派生头和 AES-GCM 请求/响应适配；重复 form/query、原始 multipart 和二进制可按实际字节保留。具体格式、账号失效、退出码与工具边界见 [执行指引](skills/miniapp-dynamic/references/execution.md)。未知签名、协议或缺凭证明确受阻，不自动套用或伪造成功。

每次实际尝试保存脱敏制品与 SHA256，replay-run.json 区分收到响应、传输失败和未发送；只有完整响应与协议期望都成立才记重放成功。执行器不自行判断漏洞，初始 findings 为空也不代表安全。输出目录独占创建，避免覆盖已有证据。


## 输出契约

- 最终 findings.json 和 evidence.json 都是数组；发现 ID 使用稳定 F-001，证据使用 EV-001，排序不重编。
- 发现状态只有 confirmed、needs_validation、rejected，没有默认确认状态。候选使用 priority，仅 confirmed 可以有 severity。
- E0 是线索，E1 是有根据的待验证路径，E2 是直接证明具体失效的证据，E3 进一步证明授权测试数据上的影响范围；证据强度不按静态/动态工具划分。
- 鉴权、支付、数据流与隐私记录复用统一 finding schema。密钥原始候选保留 secrets，不能凭格式命中直接确认。
- 动态输出包含 entry_mode、requests、findings 与 limitations，区分从流量开始和已有假设。成功重放必须有实际发送与响应的证据引用。
- 结构清单 COMPLETE 只表示已检查的声明结构齐备；未核实的质量状态为 UNKNOWN，未识别计数为 null。

详细字段以 skills 内 schema 为准。新契约移除了旧状态、字段别名、自动风险分数和 JS 报告模板表达式；已有产物需要按当前契约重新整理。

## 验证

材料与接口提取器只使用 Python 标准库并离线读取；动态执行器使用其技能 requirements.txt 中声明的依赖，开发依赖复用该文件。校验器只读取本地 schema 与证据：

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py --strict
python3 scripts/check_links.py
python3 -m unittest discover -s evals -p 'test_*.py'
python3 scripts/validate_outputs.py --evidence-dir /path/to/evidence
python3 evals/run_scenarios.py --output-dir /path/to/new-scenario-output
```

输出校验器离线检查阶段产物、最终数组、条件必填字段、ID 和引用；追加 --verify-artifacts 核对 bundle 内真实文件与 SHA256，不请求 schema URL。通过校验不能代替判断证据真实性与影响。

CI 运行格式、链接与行为回归。真实本地 HTTP/HTTPS 与代理场景检查安全/有问题/受阻、账号隔离、签名、加密与字节保真，运行后保留逐项观察和 summary.json。场景使用方式与独立 Agent 任务入口见 [评测说明](evals/README.md)。这些结果不等于真实微信兼容性或模型审计准确率；trigger-queries.csv 仍只是触发评测输入。

## 环境与边界

需要支持 Agent Skills 的客户端。CLI 安装需要 Node.js；本地脚本需要 Python 3.10+。解包、开发者工具、Reqable 或其它代理按任务选用，依赖实际版本能力。

仅测试已授权目标与账号。生产默认只读，状态变更需要明确许可、受控环境与回滚方案；不执行真实资金操作或未经授权的删除与权限变更。共享前脱敏，并按约定保留或删除原始证据。

维护约定见 CONTRIBUTING.md，设计约束见 docs/design.md，安全政策见 SECURITY.md。

## License

MIT
