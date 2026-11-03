# Design and Quality

This document records the structure, quality standards and extension rules for the skill set. It is intended for maintainers, not for the Agent during an audit.

## Architecture

The repository uses six phase-oriented skills instead of one skill per vulnerability type.

| Skill | Responsibility | Why it is separate |
|---|---|---|
| `miniapp-audit` | Scope, orchestration, quality gates | The audit loop and evidence standard must be visible before any phase starts |
| `miniapp-recon` | Material acquisition and inventory | Material completeness determines the confidence of every later conclusion |
| `miniapp-threat-model` | Business model, trust boundaries, abuse cases | Testing without a model produces noise; this phase decides what matters |
| `miniapp-static-audit` | Attack surface, secrets, data flow, authz, payment, privacy, supply chain | Static analysis produces hypotheses; the domain references stay detailed without bloating the main workflow |
| `miniapp-dynamic` | Capture, replay, mutation, multi-account verification | Dynamic work converts hypotheses into evidence and has distinct safety constraints |
| `miniapp-report` | Evidence normalization, severity, report, retest | Reporting has its own quality gate and must separate confirmed, suspected and untested |

The previous version used eleven skills. The reduction is intentional:

- Vulnerability types are references under `miniapp-static-audit`, not separate skills.
- Material checks and code restoration are parts of reconnaissance, not separate workflows.
- The orchestrator no longer duplicates detailed checklists.
- Each skill has one primary output and one quality gate.

## Skill contract

Every skill follows the Agent Skills specification:

- Directory name equals the frontmatter `name`.
- `description` states what the skill does and when to use it, using trigger-oriented phrasing and specific keywords.
- `allowed-tools` is a space-separated string.
- `metadata` values are strings.
- `SKILL.md` stays under 500 lines; detailed material lives in `references/` and `assets/`.
- Relative references resolve from the skill directory.
- No emojis, marketing language or time-sensitive claims.

## Progressive disclosure

```text
skill/
├── SKILL.md          # workflow, principles, quality gate, pointers
├── references/       # detailed checklists and domain guidance
└── assets/           # schemas, templates, rule catalogs
```

The main file answers: what is this phase, what questions does it ask, what is the quality gate, and where is the detail. References answer: how to perform a specific domain check. Assets answer: what shape does the output take.

## Audit thinking

The shared model is in `skills/miniapp-audit/references/methodology.md`:

- The client is untrusted; the server or cloud function is the trust boundary.
- The core question is which client-controlled field the server treats as trusted.
- The six lenses are Control, Input, State, Data, Money and Automation.
- Evidence levels are E0 to E3; only E2 and E3 support a confirmed finding.
- Coverage is explicit; untested paths are part of the result.

## Quality standards

### Trigger quality

Each description should pass a simple trigger test:

- It triggers on realistic audit prompts that mention the phase, the artifact or the risk.
- It does not trigger on unrelated code review or general web testing.
- It contains specific terms such as `wxapkg`, `app-service.js`, `云函数`, `越权`, `Reqable` or `复测`.

### Output quality

Each phase has a concrete output contract:

- Recon: material inventory and limitations.
- Threat model: abuse cases and prioritized hypotheses.
- Static audit: E0/E1 hypotheses with source, path and missing guard.
- Dynamic: E2/E3 evidence with reproducible requests.
- Report: confirmed, suspected and untested findings with remediation and retest criteria.

### Validation

Run:

```bash
python3 scripts/validate_skills.py
```

The validator checks frontmatter, name and directory, description, `allowed-tools`, metadata, code fences, relative references and body length. `scripts/check_links.py` checks repository-wide relative links. GitHub Actions runs both checks on push and pull request.

For spec compatibility:

```bash
skills-ref validate skills/miniapp-audit
```

### Evaluation

A complete evaluation should include:

- A trigger set with positive and negative cases.
- At least three output scenarios: a vulnerable sample, a secure sample and an incomplete-material sample.
- With-skill and without-skill baselines.
- Regression cases for previously missed findings and false positives.

Trigger queries are stored in `evals/trigger-queries.csv`. Add output evals under `evals/` when the first real audit regression set is available.

## Extension rules

### Adding a reference

- Place it in the relevant skill's `references/` directory.
- Add a pointer from `SKILL.md` with a condition: when to read it.
- Keep it focused on one domain or one decision.
- Add a table of contents if it exceeds 100 lines.

### Adding a script

- Place it in the relevant skill's `scripts/` directory.
- Use Python standard library or declare dependencies explicitly.
- Accept all input through flags, environment variables or stdin; never prompt interactively.
- Provide specific error messages and `--help`.
- Add a validation step to the skill workflow.

### Adding a skill

- Create a directory whose name matches the frontmatter `name`.
- Give it one primary responsibility and one output contract.
- Add it to `.claude-plugin/marketplace.json`.
- Add it to the README skill table.
- Run the validator and the official `skills-ref` check.

## Version history

### 2.0.1

- `inventory.py` supports raw wxapkg unpack layout.
- `extract_endpoints.py` keeps distinct dynamic URL expressions.
- Both fixes verified against a real mini program package.

### 2.0

- Reorganized into six phase-oriented skills.
- Added `miniapp-threat-model` and the shared audit methodology.
- Added evidence levels, quality gates and coverage expectations.
- Made every skill spec-compliant: name equals directory, `allowed-tools` string, metadata strings.
- Removed the invalid `@wechat/unveilr` recommendation.
- Fixed broken references and an unbalanced code fence.
- Added `scripts/validate_skills.py`.
- Added `inventory.py`, `extract_endpoints.py`, `normalize_request.py`, `check_findings.py` and `check_coverage.py` for deterministic reconnaissance, surface extraction, replay preparation, report validation and coverage validation.
- Added the Claude Code plugin marketplace manifest.
- Reworked installation around `npx skills add` and standard skill directories.

### 1.0

- Eleven skills organized by vulnerability type.
- Material completeness gate, schemas and report template.
- Initial Reqable capture integration.

## References

- Agent Skills specification: https://agentskills.io/specification
- Anthropic skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Agent Skills meta-skill: https://agentskills.io/skill.md
- OpenAI skill evals: https://developers.openai.com/blog/eval-skills
- WeChat security risks: https://developers.weixin.qq.com/miniprogram/security/basic/risk
- OWASP API Security Top 10: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- OWASP MASVS: https://mas.owasp.org/MASVS/
