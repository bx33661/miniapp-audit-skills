# 实际请求执行与账号适配

有原始请求、授权测试账号并需要实际重放时阅读。先核对目标协议和允许操作；请求计划只是执行输入，不替代授权。

## 选择执行路径

| 输入或能力 | 实际操作 | 不能当成完成的操作 |
|---|---|---|
| Reqable 现场流量 | 按授权 host/应用过滤，读取选定记录，记录会话、时间与记录 ID | 仅看到代理连接、只导出 curl |
| 已知 HTTP/1.1 请求 | 使用本技能 replay.py 或已核实的 HTTP 客户端，保存实际请求与完整相关响应 | 只创建请求标签、只生成代码 |
| Burp 或 Yakit 执行工具 | 先发现实际可用工具及参数，发送基线与改参，读取同次执行的响应 | 把 Repeater 标签或热加载函数自测当真实目标响应 |
| HTTP/2、WebSocket 或未知签名/加密 | 使用具备相应能力且可核实的工具；没有适配条件则记录 BLOCKED | 静默改协议、套相似算法后声称复现 |

Reqable capture_live_filter 只返回记录 ID，再调用 capture_live_get_by_id 读取内容。将真实方法、URL、头和 body 映射为计划；原始 body 需要保真时用 file/base64，不能通过 shell 执行导出的 curl 字符串来猜参数。没有捕获到的字段保持未知。

## 内置执行器

在本技能目录执行：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/replay.py --plan /path/to/plan.json --output-dir /path/to/new-evidence
```

使用 [请求计划契约](../assets/replay-plan.schema.json) 和 [双账号结构示例](../assets/replay-plan-example.json)。示例域名、资源和响应条件必须替换为真实授权测试材料；不能直接当作目标协议。output-dir 必须是新目录，防止覆盖已有审计结果。

计划明确 environment、scope、accounts 和 requests。scope 指定精确 origins、允许方法、请求总数、socket timeout、响应字节上限；可指定显式 HTTP proxy 与受信 CA 文件。执行器不读取环境代理、不自动跳转或重试，不关闭 TLS 验证。HTTP 方法名本身不能证明操作只读。

## 账号与会话

- 每个账号独立 origins、认证头、CookieJar 和失效规则。认证头通过 value_env 引用完整实际值，Cookie 通过 cookie_env 引用；不把 Token 写入共享计划或继承另一账号的抓包认证头。
- 用 A 的正常资源和 B 的正常资源分别建立基线，再用 A 访问 B 的测试资源。记录业务 owner/tenant 与凭证实际所属身份，不凭 Cookie 名判断归属。
- Cookie 只在账号初始化时种入；后续使用真实 Set-Cookie 更新，不把初始值每次写回。一个账号失效不会污染独立账号。
- 默认意外 401 表示会话受阻；可配置已知业务 JSON 失效信号。403 不自动等同会话过期，预期 401/403 负例也不能被误判为失效。
- 会话失效后阻塞该账号后续步骤，保存原因；获取新的授权凭证再运行，不自动登录或重放有副作用的刷新流程。

## Body 与协议保真

text 使用 UTF-8；json 是明确选择的紧凑序列化，不能假装保留原 JSON 空白；form 使用有序二元组，保留重复键。file/base64 保留原始字节，适合 multipart、二进制和已捕获密文，boundary 与 Content-Type 来自实际请求。Host、Content-Length、Transfer-Encoding、Connection 由传输层管理。

expect 校验正常请求或协议实验的状态、JSON Pointer 与正文标记。探测请求可以接受多个实际响应状态，再由分析者判断业务归属；expect 通过不等于接口安全，也不等于漏洞成立。

## 已知签名与加密

内置 hmac-sha256 只支持此规范化格式，密钥由 key_env 读取，key_encoding 为 utf8/hex/base64：

```text
UPPERCASE_METHOD + "\n" + raw_path_and_query + "\n" + unix_seconds + "\n" + fresh_nonce + "\n" + lowercase_sha256_hex(final_wire_body)
```

输出 HMAC 十六进制，默认 X-Timestamp、X-Nonce、X-Signature。每次生成新派生字段，按大小写不敏感规则替换旧头；更改业务参数后重新签名，派生变化需要记录，但不算新增业务实验变量。

AES-GCM 只支持 key_env 中 hex 编码的 16/24/32 字节密钥，以及 base64(12 字节 nonce || ciphertext || 16 字节 tag) 信封；aad 为 UTF-8。请求使用新随机 nonce，先加密最终 body 再签名；response_encryption 按相同显式格式解码后再检查业务结果。

目标排序、编码、签名覆盖字段、密钥来源或信封不同，就不适用此适配器。保留实际规则和阻塞原因，使用经验证的专用适配；不执行目标脚本、不暴力破解，也不把解密失败解释为安全。

## 证据与完成条件

执行器保存 evidence.json、dynamic-test-results.json、replay-run.json 及 captures 下的真实制品。EV-001 是脱敏计划输入，每次实际网络尝试另有 EV；未发出的步骤没有伪造 wire 证据。制品带 SHA256，目录与文件分别限制为 0700/0600。

请求/响应保留实际字节数、摘要和脱敏视图；解码视图与 wire 摘要分开。截断、解密或传输失败不能成功。脱敏覆盖配置的字段、常见凭证/个人信息及已知秘密，不保证识别一切个人数据；共享前仍需复核。

replay-run 区分 response、transport_error、not_attempted。只有完整实际响应且 expect 通过才记 succeeded；收到 403、执行成功和漏洞结论是不同事实。findings 初始为空，因为执行器不自动作漏洞判断。

退出码 0 表示所有请求完成协议期望，3 表示有阻塞/不匹配/传输失败，2 表示计划或设置错误。timeout_seconds 限制 socket 操作，系统 DNS 解析可能超时更久；宿主应提供进程期限，异常终止后按未完成记录，不推测执行结果。

仓库集成时验证：

```bash
python3 scripts/validate_outputs.py --evidence-dir /path/to/new-evidence --verify-artifacts
```

校验制品存在、SHA256 与引用，并不替代判断“这些响应是否证明具体安全边界失效”。

超限检测最多额外读取一个哨兵字节；截断时 body_bytes 仅表示实际已观察量，不能当完整长度，不保存未经完整脱敏的部分正文或完整内容摘要。

已收到响应头、正文却中断时，transport_error 保留实际 HTTP 状态；只有未发送步骤的 response_status 必须为 null。状态码已返回不能替代完整业务响应。
