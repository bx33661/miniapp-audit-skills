---
name: miniapp-audit-dataflow-tracer
description: 数据流追踪分析 - 启发式追踪 Source→Sink 路径、识别 Transform/Guard、评估注入风险（SQL/NoSQL/XSS/命令注入）
metadata:
  version: 1.0.0
  category: security-audit
  author: WxRay
  input_format: "source_dir=<path> output_dir=<path> [trace_depth=10]"
  output_schema: "../wxray-shared/schemas/dataflow-output.schema.json"
allowed-tools:
  - Bash
  - Read
  - Write
---

# Dataflow Tracer - 数据流追踪

## 功能

启发式追踪敏感数据从 Source 到 Sink 的流动路径，识别防护措施，评估注入风险。

**数据流模型**：
```
Source → [Transform₁] → [Transform₂] → ... → [Guard?] → Sink
```

**风险判断**：
- ✅ Safe: Source → Guard (有效) → Sink
- ⚠️ Risky: Source → Guard (弱) → Sink  
- ❌ Vulnerable: Source → (无 Guard) → Sink

**规则配置**: 所有模式定义位于 `../wxray-shared/rules/dataflow/`
- `source-patterns.json` - 数据入口点模式
- `sink-patterns.json` - 危险操作点模式
- `transform-patterns.json` - 数据变换模式
- `guard-patterns.json` - 防护措施模式

## 执行流程

### 步骤 1: 参数解析

解析输入参数：
- `source_dir`: 源码目录（必需）
- `output_dir`: 输出目录（必需）
- `trace_depth`: 追踪深度（可选，默认 10）

如果缺少必需参数，报错并终止。

### 步骤 2: 加载规则文件

从 `../wxray-shared/rules/dataflow/` 加载以下 JSON 规则文件：
- `source-patterns.json` - 数据入口点模式
- `sink-patterns.json` - 危险操作点模式
- `transform-patterns.json` - 数据变换模式
- `guard-patterns.json` - 防护措施模式

解析为 JSON 对象供后续使用。

### 步骤 3: 查找所有 JS 文件

查找源码目录下所有 JavaScript 文件：
- 扩展名：`.js`
- 排除：`node_modules` 目录
- 使用：`find` 命令递归搜索

### 步骤 4: 识别所有 Source（数据入口点）

遍历每个 JS 文件：
1. 读取文件内容，按行分割
2. 对每个 source pattern：
   - 编译正则表达式
   - 在每行中匹配
   - 提取变量名（捕获组）
3. 记录每个匹配：
   - `source_id`: 唯一标识（SRC-1, SRC-2...）
   - `type`: 来源类型（query_param, form_input, storage_read...）
   - `variable`: 变量名
   - `file`: 相对文件路径
   - `line`: 行号
   - `code`: 代码片段
   - `risk_level`: 风险等级（HIGH/MEDIUM/LOW）
   - `description`: 描述

输出：识别的 Source 数量。

### 步骤 5: 识别所有 Sink（危险操作点）

遍历每个 JS 文件：
1. 读取文件内容，按行分割
2. 对每个 sink pattern 的每个正则表达式：
   - 编译正则（忽略大小写）
   - 在每行中测试匹配
3. 记录每个匹配：
   - `sink_id`: 唯一标识（SINK-1, SINK-2...）
   - `type`: 危险操作类型（sql_query, command_exec...）
   - `file`: 相对文件路径
   - `line`: 行号
   - `code`: 代码片段
   - `severity`: 严重程度（CRITICAL/HIGH/MEDIUM/LOW）
   - `vulnerability`: 漏洞类型（SQL Injection, XSS...）

输出：识别的 Sink 数量。

### 步骤 6: 数据流追踪（核心算法）

对每个 Source 执行追踪：
1. 初始化队列，放入 Source 作为起点
2. 广度优先搜索（BFS）：
   - 取出当前节点
   - 检查深度是否超过 `trace_depth`，超过则跳过
   - 检查是否已访问（使用 `file:line:variable` 去重）
   - 检查附近是否有 Sink（±5 行范围内且代码包含变量）
   - 如果到达 Sink，记录完整数据流
   - 否则，查找变量的后续使用（赋值、验证、函数调用）
   - 将后续使用加入队列，继承当前的 transforms 和 guards
3. 返回所有追踪到的数据流

**数据流结构**：
- `source`: 起点信息
- `sink`: 终点信息
- `path`: 完整路径节点列表
- `transforms`: 数据变换列表
- `guards`: 防护措施列表
- `depth`: 追踪深度

输出：追踪的数据流数量。

### 步骤 7: 风险评估

对每条数据流计算风险分数：
1. **基础分**：根据 Sink 严重程度
   - CRITICAL: 10 分
   - HIGH: 7 分
   - MEDIUM: 4 分
   - LOW: 2 分
2. **防护调整**：
   - 无 Guard: +5 分
   - 有弱 Guard（无 HIGH 有效性）: +3 分
   - 有强 Guard（有 HIGH 有效性）: -3 分
3. **变换惩罚**：每个不安全变换 +1 分
4. **等级判定**：
   - ≥12 分: CRITICAL
   - ≥8 分: HIGH
   - ≥4 分: MEDIUM
   - <4 分: LOW

### 步骤 8: 生成发现列表

将每条数据流转换为标准发现格式：
- `finding_id`: DF-1, DF-2...
- `title`: "{漏洞类型}: {变量} → {Sink类型}"
- `vulnerability`: 漏洞名称
- `severity`: 风险等级
- `confidence`: 置信度（有 Guard 则 MEDIUM，否则 HIGH）
- `source`: Source 详情
- `sink`: Sink 详情
- `dataflow`: 数据流详情（source/sink 位置、transforms、guards、sanitizers）
- `description`: 中文描述
- `impact`: 影响说明
- `evidence_code`: 证据代码
- `locations`: 位置列表（source + sink）
- `remediation`: 修复建议列表
- `cwe`: CWE 编号

过滤掉 INFO 级别的发现。

### 步骤 9: 生成输出文件

组装最终输出：
- `skill`: "dataflow-tracer"
- `traced_at`: 时间戳
- `source_dir`: 源码目录
- `summary`: 统计信息
  - `sources_found`: Source 数量
  - `sinks_found`: Sink 数量
  - `flows_traced`: 数据流数量
  - `vulnerable_flows`: 高危数据流数量
- `findings`: 发现列表
- `sources_catalog`: Source 完整目录
- `sinks_catalog`: Sink 完整目录

保存为 JSON 格式到 `{output_dir}/evidence/dataflow-analysis.json`。

输出完成信息和统计数据。

## 辅助函数职责

### traceDataflow
追踪单个 Source 到所有可达 Sink 的路径，使用 BFS 算法。

### findVariableUses  
在文件中查找变量的后续使用（赋值、验证、函数调用），限制向后搜索 50 行。

### detectTransform
检测代码行是否包含数据变换操作，返回变换类型和安全性。

### detectGuard
检测代码行是否包含防护措施，返回防护类型和有效性。

### assessRisk
根据 Sink 严重性、Guard 有效性、不安全变换计算风险分数和等级。

### generateRemediation
根据漏洞类型生成具体的修复建议列表。

### getCWE
根据漏洞名称返回对应的 CWE 编号。
    }
  }
}

console.log(`✓ 识别 ${sinks.length} 个危险点`)

// 5. 数据流追踪（核心）
const allFlows = []
for (const source of sources) {
  const flows = await traceDataflow(source, sinks, jsFiles, sourceDir, traceDepth, transformPatterns, guardPatterns)
  allFlows.push(...flows)
}

console.log(`✓ 追踪 ${allFlows.length} 条数据流`)

// 6. 风险评估和生成发现
const findings = allFlows.map((flow, idx) => {
  const risk = assessRisk(flow)
  
  return {
    finding_id: `DF-${idx + 1}`,
    title: `${flow.sink.vulnerability}: ${flow.source.variable} → ${flow.sink.type}`,
    vulnerability: flow.sink.vulnerability,
    severity: risk.status,
    confidence: flow.guards.length > 0 ? 'MEDIUM' : 'HIGH',
    source: {type: flow.source.type, variable: flow.source.variable, file: flow.source.file, line: flow.source.line},
    sink: {type: flow.sink.type, file: flow.sink.file, line: flow.sink.line},
    dataflow: {
      source: {location: `${flow.source.file}:${flow.source.line}`, type: flow.source.type, variable: flow.source.variable},
      sink: {location: `${flow.sink.file}:${flow.sink.line}`, type: flow.sink.type},
      transforms: flow.transforms,
      guards: flow.guards,
      sanitizers: flow.guards.filter(g => g.effectiveness === 'HIGH').map(g => g.type)
    },
    description: `检测到数据从 ${flow.source.description} 流向 ${flow.sink.vulnerability} 点，${flow.guards.length > 0 ? `途经 ${flow.guards.length} 个防护措施` : '无防护措施'}`,
    impact: risk.vulnerable ? `可被利用进行 ${flow.sink.vulnerability} 攻击` : '存在风险但有部分防护',
    evidence_code: flow.source.code,
    locations: [{file: flow.source.file, line: flow.source.line, type: 'source'}, {file: flow.sink.file, line: flow.sink.line, type: 'sink'}],
    remediation: generateRemediation(flow),
    cwe: getCWE(flow.sink.vulnerability)
  }
})

// 7. 输出结果
const output = {
  skill: 'dataflow-tracer',
  traced_at: new Date().toISOString(),
  source_dir: sourceDir,
  summary: {
    sources_found: sources.length,
    sinks_found: sinks.length,
    flows_traced: allFlows.length,
    vulnerable_flows: findings.filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH').length
  },
  findings: findings.filter(f => f.severity !== 'INFO'),
  sources_catalog: sources,
  sinks_catalog: sinks
}

await Write({
  file_path: `${outputDir}/evidence/dataflow-analysis.json`,
  content: JSON.stringify(output, null, 2)
})

console.log(`✅ 数据流分析完成: ${findings.length} 个发现，${findings.filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH').length} 个高危`)

// ========== 辅助函数 ==========

async function traceDataflow(source, sinks, jsFiles, sourceDir, maxDepth, transformPatterns, guardPatterns) {
  const flows = []
  const queue = [{variable: source.variable, file: source.file, line: source.line, path: [source], transforms: [], guards: [], depth: 0}]
  const visited = new Set()
  
  while (queue.length > 0) {
    const current = queue.shift()
    if (current.depth > maxDepth) continue
    
    const visitKey = `${current.file}:${current.line}:${current.variable}`
    if (visited.has(visitKey)) continue
    visited.add(visitKey)
    
    // 检查是否到达 Sink
    const nearSinks = sinks.filter(s => s.file === current.file && Math.abs(s.line - current.line) <= 5 && s.code.includes(current.variable))
    for (const sink of nearSinks) {
      flows.push({source: source, sink: sink, path: current.path, transforms: current.transforms, guards: current.guards, depth: current.depth})
    }
    
    // 追踪变量后续使用
    const nextUses = await findVariableUses(current.variable, current.file, current.line, sourceDir, transformPatterns, guardPatterns)
    for (const use of nextUses) {
      queue.push({
        variable: use.variable, file: use.file, line: use.line,
        path: [...current.path, use], transforms: [...current.transforms, ...use.transforms],
        guards: [...current.guards, ...use.guards], depth: current.depth + 1
      })
    }
  }
  
  return flows
}

async function findVariableUses(variable, file, startLine, sourceDir, transformPatterns, guardPatterns) {
  const fullPath = `${sourceDir}/${file}`
  const content = await Read({file_path: fullPath})
  const lines = content.split('\n')
  const uses = []
  
  for (let i = startLine; i < Math.min(lines.length, startLine + 50); i++) {
    const line = lines[i]
    if (line.trim().startsWith('//') || !line.includes(variable)) continue
    
    // 检查赋值
    const assignMatch = line.match(new RegExp(`(\\w+)\\s*=\\s*.*${variable}`))
    if (assignMatch) {
      const newVar = assignMatch[1]
      const transform = detectTransform(line, transformPatterns)
      uses.push({type: 'assignment', variable: newVar, file: file, line: i + 1, code: line.trim(), transforms: transform ? [transform] : [], guards: []})
    }
    
    // 检查防护
    const guard = detectGuard(line, variable, guardPatterns)
    if (guard) {
      uses.push({type: 'guard', variable: variable, file: file, line: i + 1, code: line.trim(), transforms: [], guards: [guard]})
    }
  }
  
  return uses
}

function detectTransform(code, patterns) {
  for (const t of patterns) {
    if (new RegExp(t.pattern).test(code)) {
      return {type: t.type, safe: t.safe, code: code.trim()}
    }
  }
  return null
}

function detectGuard(code, variable, patterns) {
  for (const g of patterns) {
    const pattern = g.pattern.replace('{VAR}', variable)
    if (new RegExp(pattern).test(code)) {
      return {type: g.type, effectiveness: g.effectiveness, code: code.trim()}
    }
  }
  return null
}

function assessRisk(flow) {
  let riskScore = 0
  const severityScores = {CRITICAL: 10, HIGH: 7, MEDIUM: 4, LOW: 2}
  riskScore += severityScores[flow.sink.severity] || 0
  
  if (flow.guards.length === 0) {
    riskScore += 5
  } else {
    const effectiveGuards = flow.guards.filter(g => g.effectiveness === 'HIGH')
    riskScore += effectiveGuards.length === 0 ? 3 : -3
  }
  
  riskScore += flow.transforms.filter(t => !t.safe).length
  
  let status = 'LOW'
  if (riskScore >= 12) status = 'CRITICAL'
  else if (riskScore >= 8) status = 'HIGH'
  else if (riskScore >= 4) status = 'MEDIUM'
  
  return {status: status, score: riskScore, vulnerable: riskScore >= 8}
}

function generateRemediation(flow) {
  const remediations = []
  
  switch (flow.sink.vulnerability) {
    case 'SQL Injection':
      remediations.push('使用参数化查询或 ORM')
      remediations.push('对用户输入进行严格验证（类型、长度、格式）')
      remediations.push('使用白名单过滤特殊字符')
      break
    case 'NoSQL Injection':
      remediations.push('验证用户输入类型（避免对象注入）')
      remediations.push('使用严格的 Schema 验证')
      break
    case 'Command Injection':
      remediations.push('避免使用 exec/eval 等危险函数')
      remediations.push('使用白名单验证命令参数')
      break
    case 'XSS':
      remediations.push('对输出进行 HTML 转义')
      remediations.push('使用框架提供的安全渲染方法')
      break
    case 'Path Traversal':
      remediations.push('规范化路径并验证在允许目录内')
      remediations.push('使用白名单限制可访问文件')
      break
    case 'SSRF':
      remediations.push('使用 URL 白名单验证')
      remediations.push('禁止访问内网地址')
      break
    default:
      remediations.push('添加输入验证和输出编码')
  }
  
  return remediations
}

function getCWE(vulnerability) {
  const cweMap = {
    'SQL Injection': 'CWE-89',
    'NoSQL Injection': 'CWE-943',
    'Command Injection': 'CWE-78',
    'XSS': 'CWE-79',
    'Path Traversal': 'CWE-22',
    'SSRF': 'CWE-918',
    'Information Disclosure': 'CWE-200'
  }
  return cweMap[vulnerability] || 'N/A'
}
```

## 能力与限制

**能力**:
- ✅ 自动识别常见 Source 和 Sink
- ✅ 启发式数据流追踪（深度可配置）
- ✅ Transform 和 Guard 识别
- ✅ 多种漏洞类型支持（SQL/NoSQL/XSS/命令注入/路径遍历/SSRF）

**限制**（诚实声明）:
- ⚠️ **不保证 100% 路径覆盖**：复杂控制流、闭包、异步可能遗漏
- ⚠️ **不支持跨文件深度追踪**：仅追踪当前文件内数据流
- ⚠️ **启发式算法**：基于模式匹配，非完整符号执行
- ⚠️ **需人工复核**：Guard 有效性需结合业务逻辑判断

**详细算法说明**: 见 `../wxray-shared/docs/dataflow-algorithm.md`

## 输出文件

- `evidence/dataflow-analysis.json` - 数据流分析结果
