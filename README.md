# MiniApp Audit Skills

> 基于 Agent 的微信小程序安全审计工具包

全面的微信小程序安全审计 Skills 套件，提供漏洞扫描、攻击面分析、合规检查和自动化报告生成。

## 核心特性

- **11 个专业 Skills**：覆盖攻击面、凭证、权限、支付、数据流、隐私等
- **3 种审计模式**：快速（5分钟）、标准（15分钟）、深度（30分钟）
- **声明式设计**：告诉 Agent "做什么"，而非"怎么做"
- **代码还原功能**：Agent 级别反编译代码智能还原，审计准确度提升 30-50%

## 安装

### 方式一：提示词安装（推荐）

直接向 Agent 发送以下提示词：

```
请帮我安装 miniapp-audit-skills：
git clone https://github.com/bx33661/miniapp-audit-skills.git 到 Skills 目录
```

### 方式二：手动安装

```bash
cd /path/to/your/skills/directory
git clone https://github.com/bx33661/miniapp-audit-skills.git
```

## 快速开始

### 标准审计

```
调用 miniapp-audit-audit，参数：source_dir=/path/to/miniapp
```

### 其他模式

```bash
# 快速扫描（5分钟）
source_dir=/path/to/miniapp mode=quick

# 深度分析（30分钟）
source_dir=/path/to/miniapp mode=deep
```

<details>
<summary><b>📦 Skills 列表（点击展开）</b></summary>

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

</details>

<details>
<summary><b>🎯 审计模式对比</b></summary>

| 模式 | 时长 | Skills 数量 | 适用场景 |
|------|------|------------|---------|
| **quick** | ~5分钟 | 4个 | 快速筛查、初步评估 |
| **standard** | ~15分钟 | 6个 | 常规审计、合规检查 |
| **deep** | ~30分钟 | 8个 | 深度分析、高价值目标 |

</details>

<details>
<summary><b>🔄 代码还原功能（创新特性）</b></summary>

针对反编译代码质量低（变量混淆、结构损坏）的问题，提供智能还原：

**能力**：
- 变量名推断：`a` → `userId`（基于数据流和上下文）
- 结构重建：闭包展开、函数提取、嵌套优化
- 注释生成：为关键逻辑添加说明
- 映射记录：完整的变量重命名映射表

**效果**：
- 代码质量评分：42 → 78 (+36)
- 审计准确度：提升 30-50%
- 完全可验证：提供映射表供人工复核

**触发方式**：当 `material-check` 检测到低质量代码时自动提示

</details>

<details>
<summary><b>📊 输出结构</b></summary>

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

</details>

<details>
<summary><b>⚙️ 配置</b></summary>

### 共享规则和文档

`miniapp-audit-shared/` 目录包含所有 Skills 共用的规则：

- `rules/dataflow/` - 数据流分析规则（source/sink/transform/guard）
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

</details>

<details>
<summary><b>🏗️ 目录结构</b></summary>

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

</details>

## 设计原则

- **声明式/指令式**：告诉 Agent "做什么"，而非"怎么做"
- **单一数据源**：规则和标准集中维护
- **并行编排**：大规模分析任务并行执行
- **用户友好**：交互式选择，透明的时间和准确度权衡

## 兼容性

支持 Skills 机制的 Agent 环境均可使用，包括 Claude Desktop、Claude Code 等。

## 前置要求

- 支持 Skills 的 Agent 环境
- Node.js 18+（用于代码分析）
- 微信小程序解包工具（推荐使用下方工具）

## 推荐配套工具

### [WxLocated](https://github.com/bx33661/WxLocated) - macOS 小程序缓存解析工具

轻量、原生的 macOS 小程序缓存查看、源码重建与安全检查工具。

**核心功能**：
- 📂 自动扫描微信小程序缓存（支持 3.x/4.x 版本和多账户）
- 🔓 原生解析标准 wxapkg 和 V1MMWX 加密缓存包
- 🏗️ 静态重建完整源码结构（app.json、页面配置、JS、WXML、WXSS）
- 🔍 内置安全检查：包完整性验证、SHA-256 哈希、敏感信息检测
- 📊 源码质量分析：定位结构异常、编译器残留和待复核内容
- 🌐 提取 API 调用、网络域名、请求参数等安全线索
- 📦 一键导出重建工程和完整分析报告

**典型工作流**：
```
WxLocated 解包 → miniapp-audit-skills 审计 → 完整安全报告
```

**系统要求**：macOS 13+ (Apple Silicon/Intel)

[下载 WxLocated](https://github.com/bx33661/WxLocated/releases/latest) | [查看文档](https://github.com/bx33661/WxLocated)

## 许可证

MIT License

---

**欢迎 Star ⭐ | 提交 Issue 和 PR**
