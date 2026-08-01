# MiniApp Audit Skills

> 基于 Claude Agent 的微信小程序安全审计工具包

一套全面的微信小程序安全审计工具包，基于 Claude Agent SDK 构建。提供模块化的 Skills，涵盖漏洞扫描、攻击面分析、合规检查和自动化报告生成。

## 特性

- **全面覆盖**：攻击面分析、凭证扫描、权限分析、支付安全、数据流追踪、隐私合规
- **Agent 驱动架构**：基于 Claude Agent SDK，支持智能分析和并行编排
- **三种审计模式**：快速（5分钟）、标准（15分钟）、深度（30分钟）
- **声明式设计**：Skills 采用指令式风格，告诉 Agent "做什么"而非"怎么做"
- **代码还原功能**：行业首创的 Agent 级别反编译代码还原，提升审计准确度

## 安装

### 方式一：Git Clone（推荐）

```bash
cd ~/.claude/skills
git clone https://github.com/bx33661/miniapp-audit-skills.git
```

克隆后，Skills 将自动可用。

### 方式二：Git Submodule

如果你在管理多个 Skill 集合：

```bash
cd ~/.claude/skills
git submodule add https://github.com/bx33661/miniapp-audit-skills.git
```

### 验证安装

重启 Claude Desktop/Code，然后检查 Skills 是否加载：

```
/miniapp-audit-audit --help
```

## 快速开始

### 前置要求

- Claude Desktop 或 Claude Code
- Node.js 18+（用于代码分析）
- 微信小程序解包工具（如 [unwxapkg](https://github.com/wxappunpacker/unwxapkg)）

### 基本使用

**标准审计**（推荐）：
```
/miniapp-audit-audit source_dir=/path/to/miniapp
```

**快速扫描**：
```
/miniapp-audit-audit source_dir=/path/to/miniapp mode=quick
```

**深度分析**：
```
/miniapp-audit-audit source_dir=/path/to/miniapp mode=deep
```

## Skills 列表

### 主编排器

- **miniapp-audit-audit** - 主编排器，协调完整审计流程

### 核心 Skills（所有模式）

- **miniapp-audit-material-check** - 材料完整性检查 + 代码质量评估
- **miniapp-audit-attack-surface** - 攻击面分析（API、权限、域名、组件）
- **miniapp-audit-secret-scan** - 凭证泄露扫描（密钥、Token、密码）

### 标准 Skills（standard/deep 模式）

- **miniapp-audit-authz-analyzer** - 权限分析（越权风险）
- **miniapp-audit-payment-audit** - 支付安全审计

### 深度 Skills（deep 模式）

- **miniapp-audit-dataflow-tracer** - 数据流追踪（污点分析）
- **miniapp-audit-privacy-compliance** - 隐私合规检查（PIPL、微信规范）

### 辅助 Skills

- **miniapp-audit-dynamic-tester** - 动态测试（需要测试环境）
- **miniapp-audit-code-restorer** - Agent 级别代码还原
- **miniapp-audit-report-builder** - 报告生成器

## 审计模式对比

| 模式 | 时长 | Skills 数量 | 适用场景 |
|------|------|------------|---------|
| **quick** | ~5分钟 | 4个 | 快速筛查、初步评估 |
| **standard** | ~15分钟 | 6个 | 常规审计、合规检查 |
| **deep** | ~30分钟 | 8个 | 深度分析、高价值目标 |

## 代码还原功能

针对反编译代码质量低（变量混淆、结构损坏）的问题，提供智能还原：

**能力**：
- 基于数据流和上下文分析的变量名推断（`a` → `userId`）
- 结构重建（闭包展开、函数提取、嵌套优化）
- 为关键逻辑生成注释
- 生成完整的变量重命名映射表

**效果**：
- 代码质量评分提升：42 → 78 (+36)
- 审计准确度提升：30-50%
- 提供完整映射表，支持人工复核验证

**使用方式**：当 `material-check` 检测到低质量代码时自动提示。

## 输出结构

```
miniapp-audit-{timestamp}/
├── audit-report.md              # 中文审计报告
├── evidence/                    # 所有证据文件（JSON）
│   ├── material-check.json
│   ├── attack-surface.json
│   ├── secret-scan.json
│   ├── authz-findings.json
│   ├── payment-findings.json
│   ├── dataflow-analysis.json
│   └── privacy-compliance.json
├── restored/                    # 代码还原输出（可选）
│   ├── pages/
│   ├── utils/
│   └── .original/
├── restoration-map.json         # 变量重命名映射（可选）
├── restoration-report.md        # 还原报告（可选）
└── fuzzing/                     # Fuzzing 工具输出
    ├── endpoints.txt
    └── parameters.txt
```

## 配置

### 共享规则和文档

`miniapp-audit-shared/` 目录包含所有 Skills 共用的规则和文档：

- `rules/dataflow/` - 数据流分析规则（source/sink/transform/guard 模式）
- `rules/privacy/` - 隐私合规规范（PIPL、微信规范）
- `docs/` - 测试模板、算法文档、严重性标准

### 动态测试配置

启用动态测试需要创建 `test-env.json`：

```json
{
  "base_url": "https://test-api.example.com",
  "auth": {
    "headers": {"Authorization": "Bearer test-token"}
  },
  "test_accounts": [
    {"username": "test_user", "password": "test_pass"}
  ]
}
```

## 目录结构

```
.claude/skills/
├── miniapp-audit/           # 11 个审计 Skills
│   ├── audit/              # 主编排器
│   ├── material-check/     # 材料完整性
│   ├── attack-surface/     # 攻击面分析
│   ├── secret-scan/        # 凭证扫描
│   ├── authz-analyzer/     # 权限分析
│   ├── payment-audit/      # 支付安全
│   ├── dataflow-tracer/    # 数据流追踪
│   ├── dynamic-tester/     # 动态测试
│   ├── privacy-compliance/ # 隐私合规
│   ├── code-restorer/      # 代码还原
│   ├── report-builder/     # 报告生成
│   └── shared/             # Schemas 和规则
└── miniapp-audit-shared/   # 共享资源
    ├── rules/              # 检测规则
    └── docs/               # 文档
```

## 设计原则

1. **声明式/指令式风格**：Skills 告诉 Agent "做什么"，而非"怎么做"
2. **单一数据源**：规则和标准集中维护在共享目录
3. **Agent 并行编排**：大规模分析任务并行执行
4. **用户友好**：交互式选择，时间和准确度权衡透明

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT License

## 致谢

- [Claude Agent SDK](https://docs.anthropic.com/claude/docs/agent-sdk) - Agent 编排框架
- [unwxapkg](https://github.com/wxappunpacker/unwxapkg) - 微信小程序解包工具
- 微信小程序安全社区
