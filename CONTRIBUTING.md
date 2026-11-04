# Contributing

本仓库维护面向 Agent 的微信小程序安全审计技能。贡献应优先提升审计判断、证据质量和可验证性，而不是增加检查清单的长度。

## 技能结构

每个技能是一个独立目录：

```text
skills/<name>/
├── SKILL.md
├── references/
├── scripts/
└── assets/
```

规则：

- 目录名必须等于 `SKILL.md` 的 `name`。
- `description` 说明做什么、什么时候使用，并包含具体触发词。
- `SKILL.md` 只保留原则、决策点、工作流和质量门；细节放 `references/`。
- 正文控制在 500 行以内；超过时拆分。
- `allowed-tools` 使用空格分隔字符串。
- `metadata` 的值使用字符串。
- 不添加表情、营销语言或无法验证的“全面”“智能”表述。
- 新增技能时同步更新 `README.md` 和 `.claude-plugin/marketplace.json`。

## 参考文档

- 一个参考文档聚焦一个领域或一个决策。
- 超过 100 行时在顶部加入目录。
- 用条件说明何时阅读，例如“当发现设计支付回调时阅读”。
- 不复制 `SKILL.md` 已有的内容。

## 脚本

提取器、计划准备、网络传输和证据校验各自保持明确职责。提取与校验离线；动态执行器只向显式 scope 发送已授权请求。严重性、证据证明力和业务影响由分析者判断，不写成关键字评分公式。

- 提取器使用 Python 标准库；动态执行依赖在技能 requirements.txt 声明，开发依赖复用它。
- 保留实际请求字节、身份隔离与 wire/解码视图区别；拒绝静默改协议、自动重试或跳转，不执行目标脚本。
- 支持 `--help`，错误信息说明具体问题和可选值。
- 不接受交互式输入；所有参数通过命令行、环境变量或 stdin 传入。
- 为会导致漏报、误确认或错误覆盖声明的正常与失败路径添加行为回归，避免测试源码文本或模板措辞。

## 验证

提交前运行：

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py --strict
python3 scripts/check_links.py
python3 -m unittest discover -s evals -p 'test_*.py'
python3 evals/run_scenarios.py --output-dir /path/to/new-scenario-output
```

如已安装官方 `skills-ref`：

```bash
for d in skills/*/; do skills-ref validate "$d"; done
```

最终产物用 `python3 scripts/validate_outputs.py --evidence-dir <dir>` 离线验证；执行器制品追加 --verify-artifacts 核对本地文件和 SHA256。通过校验仍需复核证据内容。场景回归依据实际本地服务端观察，不能冒充真实微信客户端兼容性或模型审计准确率。

## Pull request 检查

- [ ] 技能职责单一，未与现有技能重叠
- [ ] 描述包含触发条件
- [ ] 正文低于 500 行，细节在 `references/`
- [ ] 相对引用可解析
- [ ] 脚本通过正常和异常测试
- [ ] 没有表情、营销语言或真实敏感数据
- [ ] 更新了 README、marketplace 或设计文档（如适用）

## 安全

- 只对获得明确授权的目标进行测试。
- 不在 issue、PR、fixture 或示例中包含真实用户数据、Token 或密钥。
- 涉及漏洞披露时阅读 `SECURITY.md`。
