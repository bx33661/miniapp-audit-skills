> Detailed checklist. Adapt it to the target; this is not a rigid sequence.

# Report Builder - 报告生成器

## 功能

聚合所有审计证据，生成专业的中文 Markdown 报告。

## 输入

从 `evidence/` 目录读取：
- `material-check.json` - 材料完整性检查结果
- `attack-surface.json` - 攻击面信息
- `secret-scan.json` - 凭证扫描结果
- `authz-findings.json` - 鉴权分析结果（如果有）
- `payment-findings.json` - 支付审计结果（如果有）
- `privacy-compliance.json` - 隐私合规结果（如果有）
- `dataflow-analysis.json` - 数据流追踪结果（如果有）
- `dynamic-test-results.json` - 动态测试结果（如果有）

## 报告结构

### Full 报告（完整版）

```markdown
# 微信小程序安全审计报告

## 1. 审计信息
- 项目信息
- 使用工具
- 范围与限制

## 2. 执行摘要
- 总体风险等级
- 发现统计
- 关键结论
- 修复优先级

## 3. 项目与攻击面
- 项目结构
- 权限与隐私能力
- 数据流概览

## 4. 专项分析
（用户关注点的深度分析）

## 5. 安全发现
（按严重程度排序，每个发现包含完整信息）

## 6. 待确认项
（需要服务端确认的候选）

## 7. 完整 API 清单
（所有 API 的详细列表）

## 8. 完整敏感点清单
（所有敏感信息的脱敏列表）

## 9. 加密与签名分析
（自定义加密实现）

## 10. 依赖与供应链
（第三方依赖的安全性）

## 11. 隐私与合规
（合规检查表）

## 12. 已检查但未形成发现
（覆盖的规则类别）

## 13. 限制与后续工作
（审计限制和建议）

## 14. 审计记录
（执行时间线）
```

### Executive 报告（执行摘要版）

精简版，只包含：
- 审计信息
- 执行摘要
- Top 10 安全发现
- 修复优先级
- 限制

### Compliance 报告（合规专项版）

合规检查为主：
- 隐私政策
- 权限声明一致性
- 数据收集最小化
- 用户权利（注销、删除）
- 第三方 SDK 合规

## 执行流程

### 步骤 1: 解析参数

从参数字符串提取 `evidence_dir` 和 `output_path`。如果 `evidence_dir` 缺失，立即报错。

### 步骤 2: 读取所有证据文件

依次读取以下文件，解析为 JSON 对象。文件不存在时跳过并记录警告：

- `material-check.json` - 项目元数据
- `attack-surface.json` - 攻击面信息
- `secret-scan.json` - 凭证扫描结果
- `authz-findings.json` - 鉴权分析结果
- `payment-findings.json` - 支付审计结果
- `dataflow-analysis.json` - 数据流追踪结果
- `privacy-compliance.json` - 隐私合规结果
- `dynamic-test-results.json` - 动态测试结果

### 步骤 3: 聚合所有发现

从已读取的证据文件中提取所有安全发现：
- 从 `secret-scan.json` 提取 `findings` 数组
- 从 `authz-findings.json` 提取 `findings` 数组
- 从 `payment-findings.json` 提取 `vulnerabilities` 数组
- 从 `dataflow-analysis.json` 提取 `findings` 数组
- 从 `privacy-compliance.json` 提取 `findings` 数组

将所有发现合并到统一数组中。

### 步骤 4: 按严重程度排序

按以下顺序对发现排序：CRITICAL > HIGH > MEDIUM > LOW > INFO

### 步骤 5: 计算统计信息

统计各严重程度的发现数量：
- `total_findings` - 总数
- `by_severity.CRITICAL` - 严重数量
- `by_severity.HIGH` - 高危数量
- `by_severity.MEDIUM` - 中危数量
- `by_severity.LOW` - 低危数量
- `by_severity.INFO` - 信息数量

### 步骤 6: 确定总体风险等级

根据统计结果计算总体风险：
- 存在 CRITICAL 发现 → 总体风险 = CRITICAL
- 存在 3+ HIGH 发现 → 总体风险 = HIGH
- 存在 1+ HIGH 发现 → 总体风险 = HIGH
- 存在 MEDIUM 发现 → 总体风险 = MEDIUM
- 否则 → 总体风险 = LOW

### 步骤 7: 生成报告主体

构建完整的 Markdown 报告，包含以下章节：

**1. 审计信息**
- 从 `material-check.json` 提取项目名称、AppID（脱敏）、框架、版本
- 添加审计日期和总体风险等级

**2. 执行摘要**
- 列出发现统计（带图标：）
- CRITICAL 级别时显示紧急警告

**3. 攻击面分析**
- API 端点数量和高风险端点统计
- 敏感权限清单
- 第三方依赖数量和高风险依赖统计

**4. 安全发现详情**
- 遍历所有发现，逐个渲染完整信息（调用 `renderFinding`）
- 无发现时显示" 未发现安全问题"

**5. 修复优先级**
- 调用 `renderPriorities` 生成 P0 和 P1 任务列表

**6. 审计限制**
- 说明静态分析的限制
- 建议后续工作

### 步骤 8: 生成 Fuzzing 格式输出

从 `attack-surface.json` 提取：
- `endpoints.txt` - 所有 API URL 列表（每行一个）
- `parameters.txt` - 参数化测试列表（格式：`url?param=FUZZ`）

### 步骤 9: 写入所有文件

确定输出路径：
- 如果提供 `output_path`，使用其目录
- 否则使用 `evidence_dir` 的父目录

写入三个文件：
- `report.md` - 主报告
- `endpoints.txt` - 端点列表
- `parameters.txt` - 参数列表

### 步骤 10: 输出执行摘要

打印以下信息：
- 报告路径
- 总发现数
- CRITICAL 和 HIGH 数量
- Fuzzing 文件位置

## 辅助函数职责

### `maskAppId(appId)`
对 AppID 脱敏处理：保留前 4 位和后 4 位，中间替换为 `****`。

### `renderFinding(finding, index)`
渲染单个安全发现的完整 Markdown 内容，包含：
- 标题（ID + 严重程度 + 标题）
- 属性表格（严重程度、分类、置信度、位置、CWE）
- 问题描述
- 证据代码（如果有）
- 数据流分析（如果有，调用 `renderDataflow`）
- 影响说明
- 修复建议列表
- 验证方法（如果有，调用 `renderVerification`）

### `renderDataflow(dataflow)`
格式化数据流信息：
- Source 位置和类型
- Sink 位置和类型
- Sanitizers 列表

### `renderVerification(verification)`
格式化验证方法：
- 验证步骤列表
- 预期结果

### `renderPriorities(findings)`
生成修复优先级列表：
- P0 - 列出所有 CRITICAL 发现和首要修复建议
- P1 - 列出所有 HIGH 发现
- 无高优先级问题时显示" 无高优先级问题"

## 输出文件

- `report.md` - 主报告（Markdown 格式）
- `endpoints.txt` - API 端点列表（Fuzzing 格式）
- `parameters.txt` - 参数测试列表（Fuzzing 格式）

## 报告特性

- 完全的中文报告
- 自动聚合所有模块发现
- AppID 自动脱敏
- 清晰的严重程度标识和风险评级
- 完整的证据追溯和数据流分析
- 可操作的修复建议和优先级排序
- Fuzzing 友好的端点和参数输出
- 明确的审计限制说明
