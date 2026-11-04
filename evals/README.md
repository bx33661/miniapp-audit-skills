# 请求执行场景评测

这里验证实际 HTTP、账号、签名和证据链路。服务端独立记录收到的数据，评测器先从实际响应与观察形成结果，再与场景要求比较；不是模板输出检查，也不表示模型准确率或微信真机兼容性。

## 运行

在仓库根目录安装 requirements-dev.txt 中的依赖后执行：

```bash
python3 -m unittest discover -s evals -p 'test_*.py'
python3 evals/run_scenarios.py --output-dir /path/to/new-scenario-output
```

可用 `--case ownership_safe --case ownership_vulnerable` 选择子集。输出目录必须是新路径；summary.json 记录逐项分类、实际观察、失败原因和证据位置。每个 case 保留 plan.json、process.json、observed.json、result.json 和 replay 下的规范证据。虚拟凭证只属于本地夹具。

对某个已执行 case 的制品进一步验证：

```bash
python3 scripts/validate_outputs.py --evidence-dir /path/to/new-scenario-output/ownership_safe/replay --verify-artifacts
```

## 覆盖与判定

| 类别 | 实际判定依据 |
|---|---|
| 安全与有问题 | A/B 正常业务基线、A 请求 B 测试资源、owner/record/authenticated_actor 与服务端观察 |
| 会话与凭证受阻 | 实际 401 或缺少指定凭证，该 actor 后续请求未发出，独立账号继续 |
| 签名 | 服务端验证最终 wire body 的 HMAC、时间和新 nonce；错误密钥或无适配不能成为归属结论 |
| 加密 | 真实 AES-GCM 请求/响应往返，解码业务结果与 wire 摘要分开；认证失败不能通过 |
| 参数与正文 | 重复 query/form/header 的原顺序、原始 multipart 与二进制字节确实到达上游 |
| 传输 | 真实 HTTP 代理/HTTPS CONNECT、CA 验证、拒绝未知 CA、不跟随跳转、响应超限、scope 发送前拒绝 |
| 证据 | 实际尝试与未发送分开、SHA256、私有权限、无凭证泄露、已有目录不覆盖 |

请求协议检查通过不等于安全，也不等于漏洞成立。native 执行器不输出自动漏洞结论；场景评测只对已知本地目标的具体行为分类。

## 独立 Agent 任务

可以启动一个持续运行的本地目标供新 Agent 按技能执行：

```bash
python3 -u evals/replay_fixture.py --serve --mode safe --output-dir /path/to/new-target-output
```

mode 可为 safe、vulnerable、expired。启动时输出 ready JSON，其中包括 origin、proxy_url、CA、仅供本地测试的账号环境来源和已知资源；不把 mode/漏洞标签放入 manifest。目标收到的实际请求持续保存在 observed.json，SIGTERM/SIGINT 正常关闭。

把 manifest、授权范围、技能路径和独立输出目录交给执行 Agent。要求其从实际 A/B 基线和探测响应整理发现或阻塞，不读取夹具实现及后台 ground truth，不安装或操作真实微信账号。另一位复核者用 observed.json、实际请求制品和报告核对结论。记录原始任务、技能版本、执行模型、工具、真实请求与限制；不要只保存结论截图。

这是任务级执行入口。只有真正运行并检查观察后，才能报告该次任务结果；一次成功不代表总体准确率，未运行的模式不能记为通过。

## 触发输入

trigger-queries.csv 是技能选择的正负样本。结构/执行场景回归与模型路由评测分开记录；需要实际模型输出才可计算触发或审计效果指标。普通小程序开发问题不应仅因提到 Page 或 uni-app 自动触发安全审计。
