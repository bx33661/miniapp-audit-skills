> Detailed checklist. Adapt it to the target; this is not a rigid sequence.

# Material Check - 材料完整性检查

## 功能

验证小程序审计材料的完整性和一致性：
- 自动识别材料类型（wxapkg / 缓存目录 / 源码）
- wxapkg 自动解包（支持主流工具）
- 主包、分包、插件完整性验证
- 版本一致性检查（AppID、版本号、时间戳）
- 反编译质量评估
- 生成完整性报告和缺失清单

## 执行流程

### 步骤 1: 识别材料类型

检查输入路径并识别材料类型：

**文件检测**：
- 检查路径是否为文件（`test -f`）
- 如果是文件，检查扩展名和文件类型（`file` 命令）
- 扩展名为 `.wxapkg` 或文件类型为 Zip → 标记为 `wxapkg`

**目录检测**：
- 检查路径是否为目录（`test -d`）
- 如果目录中存在 `app.json` → 标记为 `decompiled_source`
- 如果目录中包含 `*.wxapkg` 文件（`find` 命令）→ 标记为 `wechat_cache`
- 否则 → 标记为 `unknown`

**输出字段**：将识别结果保存到 `material_type` 字段（值：`wxapkg` | `wechat_cache` | `decompiled_source` | `unknown`）

---

### 步骤 2: wxapkg 解包

如果材料类型为 `wxapkg`，执行解包：

**2.1 检测解包工具**
- 检查系统是否安装 `unveilr`（推荐工具，`command -v unveilr`）
- 检查系统是否安装 `wxappUnpacker`（备选工具）
- 如果两个工具都不存在，返回 `BLOCKED` 状态并提供安装指引

**2.2 执行解包**
- 使用 `unveilr` 或 `wxappUnpacker` 解包到 `<input_path>.unpacked` 目录
- 命令：`unveilr "<input_path>" -o "<output_dir>"` 或 `wxappUnpacker "<input_path>" -o "<output_dir>"`

**2.3 验证解包结果**
- 检查解包目录中是否存在 `app.json`
- 如果不存在，返回 `BLOCKED` 状态并提示解包失败
- 如果成功，更新 `material_type` 为 `decompiled_source`，更新 `sourcePath` 为解包目录

**工具缺失时的输出**：
```json
{
  "completeness": "BLOCKED",
  "issue": "缺少解包工具",
  "next_actions": [
    "安装 WxLocated (macOS) 或 unveilr (Windows)",
    "或安装 wxappUnpacker 作为备选",
    "解包后重新运行审计"
  ]
}
```

---

### 步骤 3: 读取项目配置

读取并解析小程序配置文件：

**读取 app.json**：
- 读取 `<sourcePath>/app.json` 文件内容
- 解析 JSON 并提取：
  - `pages`：主包页面列表
  - `subPackages` 或 `subpackages`：分包声明
  - `plugins`：插件配置
  - `window`：窗口配置
  - `tabBar`：底部导航栏配置

**读取 project.config.json（可选）**：
- 检查 `<sourcePath>/project.config.json` 是否存在
- 如果存在，读取并提取：
  - `appid`：小程序 AppID
  - `projectname`：项目名称
  - `miniprogramRoot`：小程序根目录

**保存元数据**：将提取的信息保存到 `metadata` 对象

---

### 步骤 4: 验证主包完整性

检查主包关键文件是否存在：

**入口文件检查**：
- 检查 `app.js` 或 `app.ts` 是否存在（`test -f`）
- 如果缺失，记录 `CRITICAL` 级别问题：`missing_entry`

**页面文件检查**：
- 遍历 `app.json` 中声明的每个页面
- 对每个页面检查：
  - `<page>.wxml` 是否存在（页面模板）
  - `<page>.js` 是否存在（页面逻辑）
- 如果缺失，记录 `HIGH` 级别问题：`missing_page_wxml` 或 `missing_page_js`

**输出**：将所有问题保存到 `main_package.issues` 数组

---

### 步骤 5: 验证分包完整性

对比声明的分包和实际文件：

**分包目录检查**：
- 遍历 `app.json` 中声明的每个分包（`subPackages`）
- 对每个分包：
  - 检查分包根目录是否存在（`test -d`）
  - 如果目录不存在，记录 `HIGH` 级别问题：`missing_subpackage`，添加到 `missingSubpackages` 列表

**分包页面检查**：
- 对存在的分包，遍历其声明的页面
- 检查每个页面的 `.js` 文件是否存在
- 如果缺失，记录 `MEDIUM` 级别问题：`missing_subpackage_page`

**输出**：
- `subpackages.declared`：声明的分包列表
- `subpackages.found`：实际存在的分包列表
- `subpackages.missing`：缺失的分包列表
- `subpackages.issues`：所有分包问题

---

### 步骤 6: 检查插件

检查声明的插件是否存在：

**插件查找**：
- 遍历 `app.json` 中的 `plugins` 对象
- 对每个插件，在以下路径查找：
  - `miniprogram_npm/<plugin_name>`
  - `plugin-private/<plugin_name>`

**缺失记录**：
- 如果两个路径都不存在，记录 `MEDIUM` 级别问题：`missing_plugin`
- 记录插件名称和 `provider` 信息

**输出**：
- `plugins.declared`：声明的插件列表
- `plugins.issues`：插件问题列表

---

### 步骤 7: 版本一致性检查

检测是否混入不同版本的文件：

**文件时间戳分析**：
- 获取所有 `.js` 文件的修改时间戳（`find` + `stat`）
- 计算相邻文件的时间戳差异
- 如果超过 5 个文件对的时间差超过 7 天，记录 `MEDIUM` 级别问题：`potential_version_mix`

**输出**：
- `quality.version_consistency`：`OK` 或 `ISSUES`
- `quality.issues`：版本问题列表

---

### 步骤 8: 反编译质量评估

评估反编译代码的质量：

**损坏文件检查**：
- 检查非 ASCII/UTF-8 编码的 `.js` 文件数量（`file` + `grep`）
- 如果数量 > 0，记录 `HIGH` 级别问题：`corrupted_files`

**未知段检查**：
- 搜索代码中的 `__UNKNOWN__` 标记（`grep -r`）
- 如果数量 > 0，记录 `MEDIUM` 级别问题：`unknown_sections`

**代码质量评分**：
- 采样检查 20 个 `.js` 文件
- 计算三个维度的评分（0-100）：
  - **变量名混淆度** (`variable_obfuscation`)：单字母变量占比，评分越高越好
  - **代码可读性** (`code_readability`)：检查缩进、注释存在性
  - **结构完整性** (`structure_integrity`)：函数完整性评估
- 计算总体评分 (`overall_quality`)：三个维度的平均值

**质量判断**：
- `overall < 50` → `needs_restoration: true`（建议启用代码还原）
- `overall >= 50 && < 70` → 可选还原
- `overall >= 70` → 质量良好，无需还原

**输出**：
```json
{
  "code_quality": {
    "overall": 42,
    "variable_obfuscation": 35,
    "code_readability": 50,
    "structure_integrity": 40,
    "needs_restoration": true,
    "recommendation": "建议启用 Agent 级别代码还原以提升审计准确度"
  }
}
```

---

### 步骤 9: 确定完整性状态

根据收集的所有问题判断完整性闸门：

**判断规则**：
- 如果存在 `CRITICAL` 级别问题 → `BLOCKED`
- 如果 `HIGH` 级别问题 > 3 个 → `PARTIAL`
- 如果存在版本冲突问题 → `CONFLICTED`
- 如果存在任何问题但不严重 → `PARTIAL`
- 如果无任何问题 → `COMPLETE`

**输出**：将结果保存到 `completeness` 字段

---

### 步骤 10: 生成输出报告

生成完整的 JSON 报告：

**报告结构**：
```json
{
  "skill": "material-check",
  "scanned_at": "<ISO_timestamp>",
  "input_path": "<原始输入路径>",
  "material_type": "wxapkg | wechat_cache | decompiled_source",
  "completeness": "COMPLETE | PARTIAL | CONFLICTED | BLOCKED",

  "metadata": {
    "app_id": "<AppID>",
    "app_name": "<应用名称>",
    "pages_count": 10,
    "subpackages_count": 2,
    "plugins_count": 1
  },

  "main_package": {
    "status": "OK | ISSUES",
    "issues": [...]
  },

  "subpackages": {
    "declared": ["pkg1", "pkg2"],
    "found": ["pkg1"],
    "missing": ["pkg2"],
    "issues": [...]
  },

  "plugins": {
    "declared": ["plugin1"],
    "issues": [...]
  },

  "quality": {
    "version_consistency": "OK | ISSUES",
    "decompile_quality": "OK | ISSUES",
    "issues": [...]
  },

  "code_quality": {
    "overall": 42,
    "variable_obfuscation": 35,
    "code_readability": 50,
    "structure_integrity": 40,
    "needs_restoration": true,
    "recommendation": "<建议文本>"
  },

  "next_actions": ["<动作1>", "<动作2>"],
  "coverage_notes": ["<说明1>", "<说明2>"]
}
```

**保存位置**：`<output_dir>/evidence/material-check.json`

---

### 步骤 11: 生成下一步动作

根据完整性状态生成建议：

**BLOCKED**：
- 添加："修复致命问题后重新运行审计"
- 列出所有 `CRITICAL` 级别问题的修复建议

**PARTIAL**：
- 添加："可以继续审计，但需要注意覆盖限制"
- 添加："尝试获取缺失的分包或文件以提高审计完整性"

**CONFLICTED**：
- 添加："识别并拆分不同版本的文件"
- 添加："确认目标审计版本后重新整理材料"

**COMPLETE**：
- 添加："材料完整，可以开始审计"

**覆盖范围说明**：
- 如果有缺失分包，说明相关功能无法审计
- 如果有缺失插件，说明插件功能无法审计
- 如果完整，说明可以继续审计

---

## 完整性闸门说明

### COMPLETE（完整）
- 主包完整（app.json + app.js + 所有页面）
- 所有声明的分包都存在
- 所有页面文件完整（wxml + js）
- 无版本冲突
- 反编译质量良好

**审计建议**：可以继续做深度审计

---

### PARTIAL（部分缺失）
- 主包完整，但部分分包缺失
- 或部分页面文件缺失
- 或插件代码缺失

**审计建议**：
- 可以继续审计已有材料
- 在报告中明确标注缺失部分
- 覆盖范围声明中列出限制

---

### CONFLICTED（版本冲突）
- 文件时间戳差异显著
- 可能混入了不同版本的文件
- AppID 不一致

**审计建议**：
- 先拆分出单一版本
- 确认目标版本后重新整理
- 避免误报

---

### BLOCKED（严重缺失）
- 缺少 app.json 或 app.js
- 主包关键文件缺失
- 解包失败

**审计建议**：
- 无法进行有效审计
- 需要补充材料
- 给出获取材料的指引

---

## 工具优先级

按平台选择，不要假设工具已安装：

1. **WxLocated**（macOS 推荐）
   - 原生扫描/解密/重建 wxapkg，支持 3.x/4.x 和多账户
   - https://github.com/bx33661/WxLocated

2. **unveilr**（Windows 推荐）
   - 社区工具，支持 wxapkg 解包
   - https://github.com/l123wx/unveilr

3. **wxappUnpacker**（备选）
   - 社区工具，兼容性较广
   - https://github.com/xuedingmiaojun/wxappUnpacker

4. **手动指导**（工具缺失）
   - 提供安装指引，或要求用户自行解包
   - 记录未解包/未验证的文件，写入 `limitations`

---

## 输出文件

- `evidence/material-check.json` - 完整性检查结果（符合 output_schema）

---

## 代码质量评估

在完整性检查后，自动评估反编译代码质量并提供还原建议。

### 质量评分维度

1. **变量名混淆度** (variable_obfuscation: 0-100)
   - 检测单字母变量、无意义命名占比
   - 评分越高表示命名越清晰

2. **代码可读性** (code_readability: 0-100)
   - 检测代码格式化、缩进、注释存在性

3. **结构完整性** (structure_integrity: 0-100)
   - 检测函数完整性、闭包展开、控制流清晰度

4. **总体质量** (overall_quality: 0-100)
   - 三个维度的平均值

### 还原建议阈值

- `overall < 50` → 强烈建议启用 Agent 级别代码还原
- `50 ≤ overall < 70` → 可选择性还原
- `overall ≥ 70` → 代码质量良好，无需还原

### 用户交互提示（由主编排器处理）

当 `needs_restoration === true` 时，主编排器会询问用户是否启动代码还原：

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

---

## 关键能力

- 自动识别材料类型
- wxapkg 自动解包（多工具支持）
- 完整的主包、分包、插件验证
- 版本一致性检测
- **反编译代码质量评估**
- **还原建议**
- 完整性闸门判断
- 明确的下一步动作指引
