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

- 使用 Python 标准库或明确声明依赖。
- 不发起网络请求，不修改目标系统。
- 支持 `--help`，错误信息说明具体问题和可选值。
- 不接受交互式输入；所有参数通过命令行、环境变量或 stdin 传入。
- 为正常路径和失败路径添加 fixture 测试。

## 验证

提交前运行：

```bash
python3 scripts/validate_skills.py
python3 scripts/check_links.py
```

如已安装官方 `skills-ref`：

```bash
for d in skills/*/; do skills-ref validate "$d"; done
```

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
