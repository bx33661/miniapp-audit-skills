# 凭证与敏感值的上下文核实

产物为 `evidence/secret-scan.json`，遵循 [secret-scan-output.schema.json](../assets/secret-scan-output.schema.json)，`skill` 为 `miniapp-static-audit`。`secrets[]` 保存脱敏线索，不承载凭规则得出的最终严重性。规则见 [secret-patterns.yaml](../assets/rules/secret-patterns.yaml)。

## 识别候选而非直接认定泄露

- 优先使用已有扫描器或入口指定的脚本；记录真实工具、版本、扫描范围、排除项和错误。不要为了参考说明临时补造一套扫描器。
- 不允许扫描器默认向服务商验证凭证。需要在线核实有效性时，先明确现有授权范围、最小操作与停止条件；本阶段不擅自发送请求。
- 正则长度、前缀、高熵、32 位十六进制或变量名只能定位候选。结合定义、完整赋值、调用位置、发布可达性和凭证用途核实。
- AppID、商户号、云环境 ID、公开 API 标识、公钥和证书不必然是秘密；AppSecret、支付 API 密钥、签名私钥与用户会话需要按各自权限与交付边界判断。
- 私钥头不证明存在完整可用私钥；数据库 URL 不一定含凭证；JWT 格式不证明签名有效或仍在有效期；手机号、邮箱可能是客服电话或测试数据。

## 上下文和误报

读取足以识别值来源与用途的上下文，而非固定前后三行。核实它是否出现在实际发布材料、打包依赖、source map、配置、注释或示例中；这些位置影响判断，但不能按目录自动排除。

- `node_modules`、`miniprogram_npm`、压缩 JS、source map 和测试资源也可能随包交付，必须披露实际扫描覆盖；不能为了降噪全部跳过。
- 占位符或测试值需要逐条确认。真实密钥可命名为 `test_key`，真实值附近可能出现 `example`；不能用上下文单词批量过滤。
- base64 图片可解释某些长字符串，但不能据此排除同文件的其他命中。
- 同值多位置可按受控指纹归并，保留所有原始位置。不要在日志、命令、模型上下文或公共报告中复制完整值。

## 证据与影响

记录凭证种类、暴露位置、是否包含完整材料、预期保密边界、实际用途、已知权限和未核实项。源码中完整服务端秘密随客户端分发，可以形成可独立核验的直接暴露证据；无需为了证明“泄露”调用真实服务。有效性、权限和更广影响未核实就明确限制，不能追加已控制云资源之类结论。

E0 是规则线索；E1 是上下文支持的待验证路径；E2 是可复现或可独立核验的直接证据证明具体边界失效；E3 是授权测试数据上进一步证实影响范围。等级不按静态/动态划分，E2 足够后停止扩大影响。

## 脱敏与处置

- 在 `value_masked`、上下文、截图、请求和报告中使用足够遮盖的值；短值可以全部隐藏，保留前后片段不能导致可还原。
- 引用原始受控材料与证据 ID 即可，不默认创建额外明文 `secrets-sensitive.json`。确需保存原值时按已有证据访问控制处理。
- 客户端环境变量和构建配置最终仍可进入发布包，不是保密方案。服务端凭证应留在可信服务端，以权限受限的接口提供能力；已暴露凭证按实际用途轮换/撤销，并核实历史访问和残留发布物。

## 输出契约

必需顶层为 `skill`、`scanned_at`、`source_dir`、`secrets`、`limitations`，可填写真实 `tool_used` 与 `tool_version`；不写旧 `statistics` 或 `false_positives`。`secrets[]` 每项填写 `evidence_id`、`type`、`value_masked`、`file`、`line`、`context` 与 `review_status`。未复核为 `unreviewed`，上下文支持相关性为 `relevant`，有排除依据为 `excluded`；后两者必须附 `reason`，均不能写最终 `severity`。这是原始线索的复核状态，不是发现状态的兼容别名，也不直接代表漏洞确认。

进入统一发现时复用稳定 `F-001`，填写 `status`、`title`、`category`、`evidence_level`，关联非空 `evidence_refs`。`needs_validation` 填 `validation_needed`，`rejected` 填 `rejection_reason`；候选可有 `priority`，只有 `confirmed` 有 `severity`。确认需 E2/E3 及 `root_cause`、`reproduction`、`impact`、`remediation`、`preconditions`、`verification.method/test_case.expected/test_case.actual`、`retest`。未执行复测应写清步骤和通过判据。`secrets[]` 原始命中不直接进入最终风险计数，也不把它误读成 `findings[]`。
