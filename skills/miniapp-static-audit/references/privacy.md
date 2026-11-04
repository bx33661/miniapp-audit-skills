# 隐私行为与适用规则核实

产物为 `evidence/privacy-compliance.json`，遵循 [privacy-compliance-output.schema.json](../assets/privacy-compliance-output.schema.json)，`skill` 为 `miniapp-static-audit`。目标是核实数据处理事实、授权边界与适用要求，不能凭配置缺失下法律结论。

## 先核实适用范围

- 记录目标发布版本、基础库/客户端、平台规则适用时间和实际功能。开发包、体验版、发布版或旧接口的行为可能不同；材料不足时保留未核实项。
- 规则依据需要具体页面、版本/日期及适用条件。微信隐私保护指引可从 [平台文档](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/) 核实；法律要求应核对现行正式文本及处理场景，不沿用笼统的“微信2023规范”。
- `regulations` 只列实际用于判断且已核对适用性的规则；技术发现、平台要求与法律适用判断分别说明，不因技术关键词自动宣告违法。
- 平台后台配置、服务协议、隐私保护指引、服务端实现和线上交互可能不随源码交付。配置文件或源码搜索没有命中，不能证明线上没有说明或相应能力。

## 政策、授权与调用时序

- 核实用户实际可见的隐私保护指引、政策内容、进入路径、版本和可访问性；不要假定 `privacyUrl` 或 `privacy.url` 是所有小程序必须使用的统一配置。
- `__usePrivacyCheck__`、`wx.getPrivacySetting`、`wx.openPrivacyContract`、`wx.requirePrivacyAuthorize` 与相关事件按目标平台版本和实现路径判断。某个调用或配置缺失不自动构成严重问题。
- 将告知、平台授权、系统权限、业务同意与真实数据上传时间排列对照，核实拒绝、撤回和重新进入时的行为。UI 勾选或出现“同意”字样不证明授权有效。
- 有网络测试授权时才核实线上可达性；无授权或无法访问时说明未核实，不把超时、非 200 或未执行请求直接写成政策不存在。

## 权限与数据行为

从 `evidence/attack-surface.json` 和实际代码读取 `permissions`、`sensitive_apis` 及真实请求目录 `apis`；机械提取结果可能不含这些可选字段，缺失不等于无隐私调用。

| 对象 | 需要核实的事实 |
|---|---|
| `permission` | 具体 scope、目标版本要求、触发时机与用户授权结果 |
| `requiredPrivateInfos` | 仅针对适用版本明确要求列入的接口，不将全部隐私 API 一律纳入 |
| 隐私保护指引 | 后台实际声明的数据类型、目的与调用行为是否一致；源码通常不能完整代表后台 |
| 实际数据 | 返回/事件里的真实字段，后续收集、展示、保存、上传、共享及保留时间 |
| 传输 | 最终 URL、协议、发送字段与实际接收者；代码中 HTTP 字符串不能单独证明已泄露 |

`wx.login` 返回临时 code，不直接返回 OpenID/UnionID；手机号事件可能提供 code，需要服务端交换。用户资料、位置、媒体、运动等 API 的返回内容与权限随版本和功能不同，按实际字段核实。个人信息的敏感性不能仅按 API 名机械二分，尤其不能把健康/运动数据一律标为非敏感。

多余声明、收集敏感信息或缺少某处配置可以作为待核实问题，但要先确定实际处理、必要性和规则要求；不自动产生固定严重性。

## 接收者、SDK 与主体关系

- 非微信域名可能就是小程序运营者自己的后端；微信域名也不能替所有后续处理证明合规。域名和 SDK 包名不等于接收者身份。
- 核实接收主体、运营者关系、处理目的、字段、服务端转发、受托/独立处理关系和授权材料。无法确认主体时明确未核实，不直接写“第三方共享”。
- 区分仅安装、打包、初始化和实际采集/发送的 SDK。记录真实版本、初始化时机、实际行为和与政策的一致性，不按友盟、神策或插件名称预设风险等级。
- 插件声明用于定位 provider 与版本，不能自动转为违规条目。共享事实保存在受控证据中并引用；待核实接收关系写入相应 `issues` 或 `limitations`，不生成旧 `third_party_sharing` 目录字段。

## 用户权利与儿童场景

- 核实查阅、更正、复制、撤回、注销/删除的真实入口和人工渠道，以及服务端处理、保留例外、备份与受托方处理。搜索不到按钮或导出函数不直接证明权利无法行使。
- 不固定要求 JSON/CSV 导出、统一15天完成注销或仅限应用内自助渠道；按适用规则与实际承诺判断。
- 儿童关键词仅用于定位业务线索。面向对象、实际年龄范围及是否处理不满十四周岁未成年人信息需材料支持；有相关处理时核实监护人同意、专门规则、范围和删除机制。
- 不因名称含“宝宝”或源码没有“家长同意”字样就确认儿童隐私违法。

## 结构与结论

必需顶层为 `skill`、`checked_at`、`source_dir`、`regulations`、`sections` 与 `limitations`。`sections` 按实际审查领域使用 `privacy_policy`、`permissions`、`data_collection`、`third_party_sdks`、`user_rights`，适用时补充 `child_protection`。每节填写 `status: reviewed/partial/not_tested`、`issues[]` 与 `limitations[]`；partial/not_tested 另填 `reason` 和非空限制，not_tested 的 issues 必须为空。reviewed 只代表做过审查，不代表合规通过。声明、调用、数据和 SDK 目录保存在受控证据或攻击面目录中并引用，不往 section 填入 schema 未定义的目录字段，不生成 PASS/FAIL 或总质量分数。

问题放在 `sections.<section>.issues[]`，使用统一 [finding.schema.json](../../miniapp-report/assets/finding.schema.json)，编号稳定为 `F-001`，不要另建顶层 `findings[]` 代替领域容器。跨节同一根因复用编号并保留关联，不重复计数。

显式选择 `needs_validation`、`confirmed` 或 `rejected`；候选可有 `priority`，仅 confirmed 有 `severity`。E0 是线索，E1 是有根据的待验证路径，E2 是可复现或可独立核验的直接证据证明具体边界失效，E3 是授权测试数据上进一步证实影响范围；证据强度不按静态/动态划分。

确认必须有 E2/E3、非空 `evidence_refs`、明确适用要求、根因、复现、影响、修复、预期与实际、复测；法律适用仍不明确时保留待核实，不能用技术证据替代法律论证。候选不进入最终风险计数，E2 足够后停止扩大数据范围。
