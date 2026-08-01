---
name: miniapp-audit-code-restorer
description: Agent 级别反编译代码还原 - 基于上下文和数据流推断变量名、重建代码结构、生成注释，提升审计准确度
metadata:
  version: 1.0.0
  category: code-analysis
  author: WxRay
  input_format: "source_dir=<path> output_dir=<path> quality_report=<path> [mode=standard|deep]"
  estimated_time: "5-10 分钟"
allowed-tools:
  - Bash
  - Read
  - Write
  - Agent
---

# Code Restorer - 反编译代码还原

## 功能

通过 Agent 级别分析提升反编译代码质量，使其更易于人工审计和自动化分析。

**核心能力**：
1. **变量名推断** - 基于上下文和使用模式推断语义化命名
2. **结构重建** - 展开闭包、优化嵌套、提取函数
3. **注释生成** - 为关键逻辑添加说明性注释
4. **映射记录** - 生成原始→还原的完整映射表

**输入要求**：
- 反编译代码目录（quality_report 显示 `overall < 50`）
- 代码质量报告（来自 material-check）

**输出**：
- `restored/` - 还原后的代码目录
- `restoration-map.json` - 变量重命名映射表
- `restoration-report.md` - 还原报告

---

## 执行流程

### 步骤 1: 验证输入

读取代码质量报告：
- 检查 `quality_report` 文件存在
- 验证 `overall < 50`（低质量代码）
- 提取质量指标：variable_obfuscation, code_readability, structure_integrity

如果质量分数 ≥50，输出提示"代码质量良好，无需还原"并退出。

### 步骤 2: 采样分析（模式识别）

选择代表性文件进行深度分析：
- 优先选择：页面逻辑（pages/）、业务模块（utils/、services/）
- 采样数量：根据 mode 决定
  - standard 模式：10-15 个文件
  - deep 模式：20-30 个文件

对每个采样文件，调用 Agent 执行：
```
分析文件 {file_path} 的代码模式：

1. 识别常见的混淆变量模式
   - 单字母变量（a, b, t, e）的使用场景
   - 通用变量名（data, res, result）的实际用途

2. 提取命名规律
   - API 响应处理模式
   - 数据转换函数模式
   - 事件处理器模式

3. 识别框架特定模式
   - 微信小程序生命周期（onLoad, onShow）
   - 数据绑定（setData）
   - 组件通信模式

返回：该文件的命名建议和结构问题列表
```

聚合所有采样结果，提取全局命名规律和重构模式。

### 步骤 3: 变量名推断（并行处理）

将所有 JS 文件分批，每批启动一个 Agent 执行：
```
对文件 {file_path} 进行变量重命名：

输入：
- 原始代码内容
- 全局命名规律（从步骤 2）
- 文件上下文（路径、类型）

任务：
1. 识别所有需要重命名的变量
2. 基于以下规则推断新名称：
   - 数据流分析：变量来源和去向
   - 使用模式：作为参数、返回值、赋值目标
   - 上下文提示：函数名、注释、API 调用
   - 类型推断：字符串、数字、对象、数组

3. 生成重命名映射表：
   {
     "a": "userId",
     "b": "userName", 
     "t": "timestamp",
     "e": "event"
   }

4. 应用重命名并返回新代码

约束：
- 保持代码功能完全一致
- 不改变控制流和逻辑
- 新变量名遵循 camelCase
- 避免与现有变量冲突
```

每个 Agent 返回：
- 重命名后的代码内容
- 变量映射表
- 置信度评分（0-100）

### 步骤 4: 结构重建（可选，deep 模式）

对复杂文件（行数 >200 或嵌套深度 >5）启动 Agent 执行：
```
重构文件 {file_path} 的代码结构：

输入：
- 重命名后的代码（从步骤 3）
- 结构问题列表（从步骤 2）

任务：
1. 展开深度闭包（>3 层）为独立函数
2. 提取重复逻辑为公共函数
3. 优化过长函数（>100 行）
4. 简化复杂条件判断

输出：
- 重构后的代码
- 提取的函数列表
- 重构说明

约束：
- 保持功能等价
- 不引入新的依赖
- 保持微信小程序 API 兼容性
```

### 步骤 5: 注释生成

为关键代码段添加注释：
- **API 调用**：说明接口用途和参数
- **数据处理**：说明转换逻辑
- **业务逻辑**：说明关键判断和流程
- **框架钩子**：说明生命周期和触发时机

注释格式：
```javascript
// [还原] 用户登录验证 - 调用 /api/user/login
// [还原] 数据转换：后端格式 → 前端展示格式
// [还原] 页面加载钩子 - 初始化数据和绑定事件
```

使用 `[还原]` 前缀标识自动生成的注释。

### 步骤 6: 生成映射文件

聚合所有变量映射，生成 `restoration-map.json`：
```json
{
  "version": "1.0.0",
  "restored_at": "2026-08-01T12:34:56Z",
  "mode": "standard",
  "files_processed": 45,
  
  "global_mappings": {
    "a": "userId",
    "b": "userName",
    "t": "timestamp"
  },
  
  "file_mappings": {
    "pages/index/index.js": {
      "e": "event",
      "d": "data"
    }
  },
  
  "extracted_functions": [
    {
      "original_location": "pages/index/index.js:45-78",
      "new_function": "validateUserInput",
      "description": "提取的表单验证逻辑"
    }
  ]
}
```

### 步骤 7: 写入还原代码

创建 `restored/` 目录，保持原始目录结构：
- 复制所有非 JS 文件（wxml, wxss, json, 图片等）
- 写入还原后的 JS 文件
- 保留原始文件到 `restored/.original/` 备份

### 步骤 8: 生成还原报告

生成 `restoration-report.md`，包含：

```markdown
# 代码还原报告

## 概览
- 处理文件数：45 个
- 重命名变量数：328 个
- 提取函数数：12 个
- 生成注释数：156 条

## 质量提升
- 变量名混淆度：35 → 82 (+47)
- 代码可读性：50 → 78 (+28)
- 结构完整性：40 → 75 (+35)
- **总体质量**：42 → 78 (+36)

## 关键改进
1. 用户认证模块：重命名 23 个变量，提取 3 个函数
2. 订单处理模块：展开 5 个深度闭包
3. 数据转换工具：添加 18 条说明注释

## 高置信度重命名（TOP 10）
| 原名 | 新名 | 置信度 | 文件 |
|------|------|--------|------|
| a | userId | 95% | pages/profile/profile.js |
| t | timestamp | 93% | utils/time.js |
...

## 建议人工复核
- pages/payment/payment.js:45 - 变量 `x` 推断为 `amount`（置信度 68%）
- utils/crypto.js:89 - 函数提取可能影响性能

## 下一步
1. 使用 `restored/` 目录进行后续审计
2. 复核低置信度重命名（<70%）
3. 测试关键功能确保等价性
```

### 步骤 9: 输出完成信息

输出还原统计和关键指标：
```
✅ 代码还原完成

📊 处理统计：
   - 文件数：45 个
   - 重命名变量：328 个
   - 提取函数：12 个
   - 生成注释：156 条

📈 质量提升：
   - 总体质量：42 → 78 (+36)
   - 变量名清晰度：+47
   - 代码可读性：+28

📁 输出位置：
   - 还原代码：{output_dir}/restored/
   - 变量映射：{output_dir}/restoration-map.json
   - 还原报告：{output_dir}/restoration-report.md

⚠️  建议：
   - 人工复核 5 处低置信度重命名
   - 测试关键业务流程
```

---

## 变量名推断策略

### 1. 数据流分析
- **Source 追踪**：变量来自 API 响应、用户输入、存储读取
- **Sink 追踪**：变量用于渲染、API 请求、存储写入
- **Transform 识别**：变量经过的转换和处理

### 2. 使用模式匹配
```
模式：res.data.user.id
推断：userId

模式：wx.setStorageSync('token', x)
推断：x → authToken

模式：function(a) { return a.name + a.age }
推断：a → user 或 person
```

### 3. 上下文提示
- **函数名**：getUserInfo → 参数推断为 userId
- **API 路径**：/api/order/detail → 返回值推断为 orderDetail
- **事件处理**：onTapSubmit → 参数推断为 event

### 4. 类型推断
```
a === 'admin' → a 可能是 role
parseInt(b) → b 可能是 数值字符串，如 price, count
c.length > 0 → c 可能是 数组或字符串，如 list, items
```

---

## 能力与限制

**能力**：
- ✅ 基于上下文的智能变量重命名
- ✅ 深度闭包展开和函数提取
- ✅ 自动注释生成
- ✅ 完整的映射记录

**限制**：
- ⚠️ **不保证 100% 准确**：低置信度重命名需人工复核
- ⚠️ **不改变运行时行为**：仅提升可读性，不修复 bug
- ⚠️ **需要较长时间**：standard 模式 5-10 分钟，deep 模式 15-30 分钟
- ⚠️ **依赖 Agent 分析**：复杂代码可能推断不准确

---

## 输出文件

- `restored/` - 还原后的代码目录
- `restoration-map.json` - 变量映射表
- `restoration-report.md` - 还原报告
- `restored/.original/` - 原始文件备份

---

## 使用场景

**适合还原**：
- 变量名混淆度 >60%（大量单字母变量）
- 代码可读性 <50（格式混乱、无注释）
- 结构完整性 <50（深度嵌套、闭包未展开）

**不建议还原**：
- 总体质量 ≥70（质量已足够好）
- 仅为合规审计（不涉及复杂逻辑分析）
- 时间紧迫（还原需要 5-30 分钟）

---

## 与主流程集成

material-check 输出 `code_quality.needs_restoration = true` 时，audit 主编排器询问用户：
```
检测到反编译代码质量较低（评分：42/100）
- 变量名混淆：65% 的变量是单字母命名
- 结构完整性：部分函数闭包未展开

是否启动 Agent 级别代码还原？
- 还原时间：预计 5-10 分钟
- 还原内容：变量名推断、结构重建、注释生成
- 审计准确度提升：约 30-50%

[Y] 是，启动还原  [N] 否，继续当前代码审计
```

用户选择 Y 后，调用本 Skill。
