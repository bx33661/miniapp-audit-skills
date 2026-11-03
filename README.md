# MiniApp Audit Skills

面向 Agent 的微信小程序安全审计技能集。核心是审计思想、信任边界和证据标准，而不是把审计写成僵化的步骤清单。

## 设计原则

- **审计思想优先。** 技能提供问题、判断标准和取舍，不替代分析。
- **证据优先。** 模式匹配只是假设；只有可复现的行为才能写成已确认漏洞。
- **业务语境优先。** 先理解角色、资产、资金流和状态机，再选择测试方法。
- **渐进披露。** 主文件只保留每次都会用到的流程；细节放在 `references/`，模板放在 `assets/`。
- **最小影响。** 默认只读；不执行真实支付、退款、删除或权限变更。
- **规范兼容。** 目录名与 `name` 一致；`allowed-tools` 使用空格分隔字符串；元数据值为字符串。

## 技能

| Skill | 用途 | 主要产出 |
|---|---|---|
| `miniapp-audit` | 规划与编排审计，维护质量门 | 审计会话、范围、覆盖与结论 |
| `miniapp-recon` | 获取、解密、解包并盘点材料 | 资产清单、完整性与限制 |
| `miniapp-threat-model` | 建模业务、角色、状态与信任边界 | 威胁模型、滥用用例、测试计划 |
| `miniapp-static-audit` | 审查攻击面、凭证、数据流、鉴权、支付、隐私与供应链 | E0/E1 假设与测试用例 |
| `miniapp-dynamic` | 用 Reqable 抓包，重放与改参验证 | E2/E3 证据与复现步骤 |
| `miniapp-report` | 归一化证据，评级并生成报告 | 发现、覆盖率、修复与复测标准 |

## 审计循环

```text
范围与授权
  → 材料与资产
  → 业务与威胁建模
  → 静态分析（假设）
  → 动态验证（证据）
  → 报告与修复
  → 复测与关闭
```

循环是迭代的。发现可能要求回到建模、补材料或重新设计测试。

## 安装

### 方式一：skills CLI（推荐）

```bash
npx skills add bx33661/miniapp-audit-skills
```

该命令适用于支持 Agent Skills 的客户端，包括 Claude Code、Codex、Cursor 等。安装时选择本仓库的六个技能。

### 方式二：Claude Code 插件市场

```text
/plugin marketplace add bx33661/miniapp-audit-skills
/plugin install miniapp-audit@miniapp-audit-skills
```

### 方式三：手动安装

将 `skills/` 下的六个技能目录复制到客户端使用的技能目录。以下命令在仓库根目录执行；克隆位置按实际路径替换。

```bash
# 项目级 Claude Code
mkdir -p .claude/skills
cp -R skills/miniapp-* .claude/skills/

# 用户级 Claude Code
mkdir -p ~/.claude/skills
cp -R skills/miniapp-* ~/.claude/skills/

# 跨客户端约定
mkdir -p .agents/skills
cp -R skills/miniapp-* .agents/skills/
```

注意：

- 复制的是 `skills/miniapp-*` 这些**技能目录**，不是仓库根目录。
- 每个技能目录必须直接位于技能根目录下，并包含 `SKILL.md`。
- 不要保留额外的命名空间层级，否则部分客户端无法发现技能。

### 验证安装

```bash
ls .claude/skills
# 应看到六个 miniapp-* 目录

# 在仓库内
python3 scripts/validate_skills.py

# 在目标项目中验证手动安装
python3 /path/to/miniapp-audit-skills/scripts/validate_skills.py --root .claude/skills
```

如已安装官方 `skills-ref`：

```bash
skills-ref validate skills/miniapp-audit
```

### 安全提示

技能以 Agent 权限运行。安装前审阅 `SKILL.md`、`references/` 和 `scripts/`，不要安装来源不明的第三方技能。

本仓库的脚本只使用 Python 标准库，不发起网络请求：`inventory.py` 和 `extract_endpoints.py` 只读取本地文件，`normalize_request.py` 只生成模板，`check_findings.py` 和 `check_coverage.py` 只校验本地 JSON。

## 使用

技能会根据描述自动触发；也可以显式指定：

```text
使用 miniapp-audit 规划这次小程序审计，材料在 /path/to/wxapkg。
使用 miniapp-recon 解包并生成资产清单。
使用 miniapp-threat-model 对登录、下单和支付流程建模。
使用 miniapp-static-audit 审查越权、支付逻辑和隐私声明。
使用 miniapp-dynamic 通过 Reqable 抓包并验证越权假设。
使用 miniapp-report 汇总证据并生成报告。
```

一次典型审计：

1. `miniapp-audit` 明确范围、授权和质量门。
2. `miniapp-recon` 建立可信的材料基线，记录缺失项。
3. `miniapp-threat-model` 识别资产、角色、状态和滥用路径。
4. `miniapp-static-audit` 生成有文件、行号和数据流的假设。
5. `miniapp-dynamic` 在真实小程序中重放与改参，形成 E2/E3 证据。
6. `miniapp-report` 区分已确认、待确认和未测试，给出修复与复测标准。

## 仓库结构

```text
.
├── skills/
│   ├── miniapp-audit/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   └── assets/
│   ├── miniapp-recon/          # SKILL.md, references/, scripts/, assets/
│   ├── miniapp-threat-model/   # SKILL.md, references/
│   ├── miniapp-static-audit/   # SKILL.md, references/, scripts/, assets/
│   ├── miniapp-dynamic/        # SKILL.md, references/, scripts/, assets/
│   └── miniapp-report/         # SKILL.md, references/, scripts/, assets/
├── .github/
│   └── workflows/
│       └── validate.yml
├── evals/
│   └── trigger-queries.csv
├── docs/
│   └── design.md
├── scripts/
│   ├── validate_skills.py
│   └── check_links.py
├── .claude-plugin/
│   └── marketplace.json
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
└── LICENSE
```

每个技能以独立目录组织。部分技能会引用套件内的共享方法论，因此建议整套安装；跨阶段的协作通过输入和输出数据完成。

## 质量与验证

- `scripts/validate_skills.py` 检查 frontmatter、名称与目录、描述、`allowed-tools`、元数据、代码围栏、断链和正文长度。
- `scripts/check_links.py` 检查 README、docs 和 skills 中的相对链接。
- GitHub Actions 在 push 和 pull request 时运行两个检查脚本。
- 官方 `skills-ref` 用于验证 Agent Skills 规范兼容性。
- 新增或修改技能后，至少运行一次本地验证。
- 发现应通过证据分级：E0/E1 为假设，E2/E3 为已确认。
- 报告应区分已确认、待确认和未测试，并给出复测标准。
- `evals/trigger-queries.csv` 提供 24 条触发测试，覆盖六个技能和负样本。

## 环境要求

- 支持 Agent Skills 的客户端。
- Node.js 18 或更高版本，用于 `npx skills` 和 JavaScript 分析工具。
- Python 3.10 或更高版本，用于本地验证脚本。
- 可选工具：WxLocated、unveilr、wxappUnpacker、微信开发者工具、Reqable、Yakit、Frida。

## 范围与限制

- 仅用于获得明确授权的安全测试。
- 默认只读；支付、退款、删除和权限变更仅在受控测试环境中进行。
- 工具版本、平台能力和微信规范会变化；使用前核对官方文档。
- 本仓库不构成法律意见，也不保证通过平台审核。

## License

MIT
