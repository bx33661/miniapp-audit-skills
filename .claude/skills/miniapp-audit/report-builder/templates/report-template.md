# 微信小程序安全审计报告

> - 报告编号：`${session.session_id}`
> - 生成时间：`${session.created_at}`
> - 审计模式：`${session.mode}`

## 1. 审计信息

| 项目 | 内容 |
| --- | --- |
| 项目名称 | `${metadata.app_name}` |
| AppID | `${metadata.app_id_masked}` |
| 源码目录 | `${session.input_path}` |
| 框架 | `${metadata.framework}` |
| 小程序版本 | `${metadata.version || '未知'}` |
| 审计范围 | `${session.scope}` |
| 用户关注点 | `${session.focus.join(', ') || '无'}` |
| 报告路径 | `${session.output_dir}/report.md` |

### 1.1 使用工具

| 工具 | 版本 | 用途 | 状态 |
| --- | --- | --- | --- |
${tools.map(t => `| ${t.name} | ${t.version} | ${t.purpose} | ${t.status} |`).join('\n')}

### 1.2 范围与限制

- **已覆盖**：${coverage.covered.join('、')}
- **未覆盖**：${coverage.uncovered.join('、')}
- **关键限制**：${limitations.join('、')}

---

## 2. 执行摘要

### 2.1 总体风险

**总体风险等级：${overall_risk}**

${executive_summary}

### 2.2 发现统计

| 严重程度 | 已验证 | 待服务端确认 | 工具候选 | 合计 |
| --- | ---: | ---: | ---: | ---: |
| Critical | ${stats.verified.CRITICAL} | ${stats.server.CRITICAL} | ${stats.tool.CRITICAL} | ${stats.total.CRITICAL} |
| High | ${stats.verified.HIGH} | ${stats.server.HIGH} | ${stats.tool.HIGH} | ${stats.total.HIGH} |
| Medium | ${stats.verified.MEDIUM} | ${stats.server.MEDIUM} | ${stats.tool.MEDIUM} | ${stats.total.MEDIUM} |
| Low | ${stats.verified.LOW} | ${stats.server.LOW} | ${stats.tool.LOW} | ${stats.total.LOW} |
| Info | ${stats.verified.INFO} | ${stats.server.INFO} | ${stats.tool.INFO} | ${stats.total.INFO} |
| **合计** | **${stats.verified.total}** | **${stats.server.total}** | **${stats.tool.total}** | **${stats.total.all}** |

### 2.3 关键结论

${key_conclusions.map((c, i) => `${i+1}. ${c}`).join('\n')}

### 2.4 修复优先级

| 优先级 | 建议 | 关联发现 | 完成判据 |
| --- | --- | --- | --- |
${priorities.map(p => `| ${p.priority} | ${p.recommendation} | ${p.finding_id} | ${p.acceptance} |`).join('\n')}

---

## 3. 项目与攻击面

### 3.1 项目结构

| 类型 | 数量 | 关键项 |
| --- | ---: | --- |
| 页面 | ${structure.pages_count} | ${structure.key_pages.join('、')} |
| 分包 | ${structure.subpackages_count} | ${structure.subpackages.join('、')} |
| 自定义组件 | ${structure.components_count} | ${structure.key_components.join('、')} |
| 插件 | ${structure.plugins_count} | ${structure.plugins.join('、') || '无'} |
| 云函数 | ${structure.cloud_functions_count} | ${structure.cloud_functions.join('、') || '无'} |
| WebView | ${structure.webviews_count} | ${structure.webviews.join('、') || '无'} |
| 第三方依赖 | ${structure.dependencies_count} | ${structure.key_dependencies.join('、')} |

### 3.2 权限与隐私能力

| API/能力 | 权限声明 | 调用位置 | 数据类型 | 业务目的 | 结论 |
| --- | --- | --- | --- | --- | --- |
${permissions.map(p => `| ${p.api} | ${p.declared} | ${p.location} | ${p.data_type} | ${p.purpose} | ${p.conclusion} |`).join('\n')}

### 3.3 数据流概览

\`\`\`text
${dataflow_diagram}
\`\`\`

---

## 4. 专项分析

${focus_sections.length === 0 ? '> 用户未指定关注点；关键业务已纳入通用审计。' : ''}

${focus_sections.map(section => `
### 4.${section.index} ${section.title}

- **目标**：${section.target}
- **调用位置**：${section.locations.join('、')}
- **数据流**：${section.dataflow}
- **已有防护**：${section.guards.join('、') || '未发现'}
- **结论**：${section.conclusion}
- **后续验证**：${section.next_steps.join('；')}
`).join('\n')}

---

## 5. 安全发现

${findings.map((f, idx) => `
### F-${String(idx + 1).padStart(3, '0')} [${f.severity}] ${f.title}

| 属性 | 内容 |
| --- | --- |
| 规则 | ${f.rule_id} |
| 分类 | ${f.category} |
| 状态 | ${f.status} |
| 置信度 | ${f.confidence} |
| CWE | ${f.cwe || 'N/A'} |
| 位置 | [${f.locations[0].file}:${f.locations[0].line}](${f.locations[0].file}#L${f.locations[0].line}) |
${f.locations.length > 1 ? `| 其他位置 | ${f.locations.slice(1).map(l => `${l.file}:${l.line}`).join('、')} |` : ''}
| 检测来源 | ${f.detection_source} |

#### 问题描述

${f.description}

#### 最小证据

\`\`\`javascript
${f.evidence_code}
\`\`\`

#### 数据流与防护

\`\`\`text
${f.dataflow_text}
\`\`\`

- **已有防护**：${f.guards.join('、') || '未发现'}
- **防护缺口**：${f.missing_guards.join('、')}

#### 影响

${f.impact}

#### 修复建议

${f.remediation.map((r, i) => `${i+1}. ${r}`).join('\n')}

#### 验证方法

${f.verification_method === 'dynamic_test' ? `
\`\`\`http
${f.test_case.request}
\`\`\`

- **成功判据**：${f.test_case.expected}
- **修复判据**：${f.test_case.fixed}
` : `
- **验证方法**：${f.verification_method}
- **验证步骤**：${f.verification_steps.join('；')}
`}

---
`).join('\n')}

## 6. 待确认项

${pending.length === 0 ? '> 无待确认项。' : ''}

| ID | 候选 | 位置 | 缺少证据 | 建议补充 |
| --- | --- | --- | --- | --- |
${pending.map(p => `| ${p.id} | ${p.candidate} | ${p.location} | ${p.missing_evidence} | ${p.requested_material} |`).join('\n')}

---

## 7. 完整 API 清单

| ID | 类型 | 方法 | 端点/函数 | 参数 | 认证线索 | 调用位置 | 风险关联 |
| --- | --- | --- | --- | --- | --- | --- | --- |
${apis.map(a => `| ${a.id} | ${a.type} | ${a.method} | \`${a.url}\` | ${a.params.join(', ')} | ${a.auth.type} | ${a.locations[0].file}:${a.locations[0].line} | ${a.related_findings.join(', ') || '-'} |`).join('\n')}

### 7.1 域名

| 域名 | 协议 | 用途 | 出现位置 | 环境 |
| --- | --- | --- | --- | --- |
${domains.map(d => `| ${d.domain} | ${d.protocol} | ${d.purpose} | ${d.location} | ${d.environment} |`).join('\n')}

---

## 8. 完整敏感点清单

| ID | 类型 | 脱敏值/字段 | 位置 | 暴露面 | 保护 | 风险 | 关联发现 |
| --- | --- | --- | --- | --- | --- | --- | --- |
${sensitive_points.map(s => `| ${s.id} | ${s.type} | \`${s.masked_value}\` | ${s.location} | ${s.exposure.join('、')} | ${s.protection} | ${s.risk} | ${s.related_findings.join(', ') || '-'} |`).join('\n')}

---

## 9. 加密与签名分析

${crypto.length === 0 ? '> 未发现自定义加密/签名实现；传输保护另见 API 清单。' : ''}

| 位置 | 算法/用途 | Key/IV/nonce 来源 | 完整性/重放保护 | 结论 |
| --- | --- | --- | --- | --- |
${crypto.map(c => `| ${c.location} | ${c.algorithm} | ${c.key_source} | ${c.integrity_protection} | ${c.assessment} |`).join('\n')}

---

## 10. 依赖与供应链

| 依赖 | 锁定版本 | 数据源 | 已知漏洞/配置问题 | 结论 |
| --- | --- | --- | --- | --- |
${dependencies.map(d => `| ${d.name} | ${d.version} | ${d.source} | ${d.issues.join('；') || '无'} | ${d.assessment} |`).join('\n')}

${supply_chain_notes.length > 0 ? `\n**注意事项**：\n${supply_chain_notes.map(n => `- ${n}`).join('\n')}` : ''}

---

## 11. 隐私与合规

| 检查项 | 证据 | 结论 | 建议 |
| --- | --- | --- | --- |
${compliance.map(c => `| ${c.item} | ${c.evidence} | ${c.conclusion} | ${c.recommendation} |`).join('\n')}

---

## 12. 已检查但未形成发现

${checked_no_findings.map(c => `- **${c.category}**：${c.scope}`).join('\n')}

---

## 13. 限制与后续工作

${limitations_detailed.map(l => `- ${l}`).join('\n')}

---

## 14. 审计记录

| 时间 | 动作 | 结果 |
| --- | --- | --- |
${audit_log.map(log => `| ${log.time} | ${log.action} | ${log.result} |`).join('\n')}

---

## 附录

### A. 证据文件

- [attack-surface.json](evidence/attack-surface.json)
- [secrets.json](evidence/secrets.json)
${additional_evidence.map(e => `- [${e}](evidence/${e})`).join('\n')}

### B. 发现详情

${findings.map((f, idx) => `- [F-${String(idx + 1).padStart(3, '0')}](findings/F-${String(idx + 1).padStart(3, '0')}.json)`).join('\n')}

---

*报告生成时间：${new Date().toISOString()}*
