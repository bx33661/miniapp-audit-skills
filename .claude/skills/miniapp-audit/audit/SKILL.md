---
name: miniapp-audit-audit
description: 微信小程序安全审计主编排器 - 协调完整审计流程，支持 quick/standard/deep 三种模式，自动编排材料检查、攻击面分析、漏洞扫描、报告生成
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "source_dir=<path> [mode=quick|standard|deep] [output_dir=<path>]"
  requires_skills:
    - miniapp-audit-material-check
    - miniapp-audit-attack-surface
    - miniapp-audit-secret-scan
    - miniapp-audit-report-builder
  optional_skills:
    - miniapp-audit-authz-analyzer
    - miniapp-audit-payment-audit
    - miniapp-audit-dataflow-tracer
    - miniapp-audit-privacy-compliance
    - miniapp-audit-dynamic-tester
    - miniapp-audit-code-restorer
allowed-tools:
  - Bash
  - Read
  - Write
  - Skill
---

# WxRay Audit - 主编排 Skill

## 功能

协调完整的微信小程序安全审计流程：
- 材料完整性验证（自动解包 wxapkg）
- 攻击面映射（API、权限、域名、组件）
- 安全漏洞扫描（凭证泄露、越权、支付、注入）
- 隐私合规检查（PIPL、微信规范）
- 动态测试验证（可选）
- 中文审计报告生成

## 审计模式

- **quick**: 快速扫描（材料检查 + 攻击面 + 凭证扫描）~5分钟
- **standard**: 标准审计（quick + 权限分析 + 支付审计）~15分钟
- **deep**: 深度分析（standard + 数据流追踪 + 隐私合规）~30分钟

## 参数说明

- `source_dir`: 小程序源码目录或 wxapkg 文件路径（必需）
- `mode`: 审计模式，默认 standard
- `output_dir`: 输出目录，默认 `./miniapp-audit-audit-{timestamp}`

## 使用示例

```bash
# 标准审计
/miniapp-audit-audit source_dir=/path/to/miniapp

# 快速扫描
/miniapp-audit-audit source_dir=/path/to/miniapp mode=quick

# 深度分析
/miniapp-audit-audit source_dir=/path/to/miniapp mode=deep

# 自定义输出目录
/miniapp-audit-audit source_dir=/path/to/miniapp output_dir=./my-audit
```

## 执行流程

### 步骤 1: 初始化

1. 解析参数：从输入中提取 `source_dir`、`mode`、`output_dir`
2. 验证必需参数：`source_dir` 必须存在，否则报错并显示用法
3. 创建输出目录结构：`${output_dir}/evidence/`

### 步骤 2: Phase 1 - 材料完整性检查（阻塞）

1. 调用 `miniapp-audit-material-check`，传入 `input_path=${source_dir} output_dir=${output_dir}`
2. 读取材料检查结果：`${output_dir}/evidence/material-check.json`
3. 如果完整性为 BLOCKED，终止审计并提示用户补充材料
4. 如果输入为 wxapkg 且已解包，更新 `source_dir` 为解包后目录

### 步骤 2.5: 代码质量评估与还原（可选，交互式）

1. 检查材料检查结果中的 `code_quality` 字段
2. 如果 `code_quality.overall < 50` 且 `code_quality.needs_restoration = true`：
   - 提取质量指标并展示给用户：
     ```
     检测到反编译代码质量较低（评分：{overall}/100）
     - 变量名混淆：{variable_obfuscation}% 的变量是单字母命名
     - 代码可读性：{code_readability}/100
     - 结构完整性：{structure_integrity}/100

     是否启动 Agent 级别代码还原？
     - 还原时间：预计 5-10 分钟（standard 模式）或 15-30 分钟（deep 模式）
     - 还原内容：变量名推断、结构重建、注释生成
     - 审计准确度提升：预计 30-50%

     [Y] 是，启动还原  [N] 否，继续当前代码审计  [S] 跳过并记录
     ```
   
3. 如果用户选择 Y：
   - 调用 `miniapp-audit-code-restorer`，参数：`source_dir=${source_dir} output_dir=${output_dir} quality_report=${output_dir}/evidence/material-check.json mode=standard`
   - 等待还原完成（输出包含还原统计和质量提升数据）
   - 更新 `source_dir` 为还原后目录：`${output_dir}/restored/`
   - 在后续审计中使用还原后的代码
   
4. 如果用户选择 N 或 S：
   - 继续使用原始反编译代码
   - 在报告中标注"代码质量低，未经还原，可能影响审计准确度"

5. 如果 `code_quality.overall >= 50`：
   - 跳过此步骤，直接进入核心扫描阶段

### 步骤 3: Phase 2 - 核心扫描

**所有模式**：
1. 调用 `miniapp-audit-attack-surface`，参数：`source_dir=${source_dir} output_dir=${output_dir}`
2. 调用 `miniapp-audit-secret-scan`，参数：`source_dir=${source_dir} output_dir=${output_dir}`

**standard 和 deep 模式额外执行**：
3. 调用 `miniapp-audit-authz-analyzer`，参数：`source_dir=${source_dir} output_dir=${output_dir} attack_surface=${output_dir}/evidence/attack-surface.json`
4. 调用 `miniapp-audit-payment-audit`，参数：`source_dir=${source_dir} output_dir=${output_dir} attack_surface=${output_dir}/evidence/attack-surface.json`

### 步骤 4: Phase 3 - 深度分析（仅 deep 模式）

1. 调用 `miniapp-audit-dataflow-tracer`，参数：`source_dir=${source_dir} output_dir=${output_dir}`
2. 调用 `miniapp-audit-privacy-compliance`，参数：`source_dir=${source_dir} output_dir=${output_dir} attack_surface=${output_dir}/evidence/attack-surface.json`

### 步骤 5: 生成报告

1. 调用 `miniapp-audit-report-builder`，参数：`output_dir=${output_dir}`
2. 返回审计结果摘要，包括：
   - 审计状态（SUCCESS）
   - 审计模式（quick/standard/deep）
   - 材料完整性等级
   - 输出目录路径
   - 报告文件路径：`${output_dir}/audit-report.md`
   - 证据目录路径：`${output_dir}/evidence/`

## 输出结构

```
miniapp-audit-audit-{timestamp}/
├── audit-report.md              # 中文审计报告
├── evidence/                    # 所有证据文件
│   ├── material-check.json
│   ├── attack-surface.json
│   ├── secret-scan.json
│   ├── authz-findings.json      # standard/deep 模式
│   ├── payment-findings.json    # standard/deep 模式
│   ├── dataflow-analysis.json   # deep 模式
│   └── privacy-compliance.json  # deep 模式
├── restored/                    # 代码还原输出（可选）
│   ├── pages/
│   ├── utils/
│   ├── .original/               # 原始文件备份
│   └── ...
├── restoration-map.json         # 变量重命名映射表（可选）
├── restoration-report.md        # 代码还原报告（可选）
└── fuzzing/                     # Fuzzing 工具输出（可选）
    ├── endpoints.txt
    └── parameters.txt
```

## 错误处理

- 材料 BLOCKED：提示解包或补充材料后终止
- 材料 PARTIAL：继续审计但在报告中标注覆盖限制
- 材料 CONFLICTED：警告版本冲突但继续
- Skill 执行失败：记录错误但继续其他 Skills

## 注意事项

1. **并行执行**: 当前顺序执行确保稳定性，未来版本将支持并行
2. **动态测试**: 需要用户单独提供 test-env.json 并调用 `/miniapp-audit-dynamic-tester`
3. **材料质量**: 审计质量直接依赖材料完整性，建议使用官方解包工具
4. **时间估算**: quick ~5min, standard ~15min, deep ~30min（取决于代码规模）
5. **代码还原**: 低质量反编译代码可选择 Agent 级别还原，需额外 5-30 分钟但显著提升审计准确度

## 相关 Skills

- `/miniapp-audit-material-check` - 单独检查材料完整性
- `/miniapp-audit-attack-surface` - 单独提取攻击面
- `/miniapp-audit-secret-scan` - 单独扫描凭证
- `/miniapp-audit-code-restorer` - 单独执行代码还原
- `/miniapp-audit-report-builder` - 单独生成报告
