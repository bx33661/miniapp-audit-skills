# MiniApp Audit Skills

> WeChat Mini Program Security Audit Toolkit for Claude Agent

A comprehensive security audit toolkit for WeChat Mini Programs, powered by Claude Agent SDK. Provides modular skills covering vulnerability scanning, attack surface analysis, compliance checking, and automated reporting.

## Features

- **Comprehensive Coverage**: Attack surface analysis, credential scanning, authorization analysis, payment security, data flow tracing, and privacy compliance
- **Agent-Driven Architecture**: Built on Claude Agent SDK with intelligent analysis and parallel orchestration
- **Three Audit Modes**: Quick (5 min), Standard (15 min), Deep (30 min)
- **Declarative Design**: Skills use instructional style, telling agents what to do rather than how
- **Code Restoration**: Industry-first agent-level decompiled code restoration for improved audit accuracy

## Installation

### Option 1: Git Clone (Recommended)

```bash
cd ~/.claude/skills
git clone https://github.com/bx33661/miniapp-audit-skills.git
```

After cloning, the skills will be available at `~/.claude/skills/miniapp-audit-skills/.claude/skills/`

### Option 2: Git Submodule

If you're managing multiple skill sets:

```bash
cd ~/.claude/skills
git submodule add https://github.com/bx33661/miniapp-audit-skills.git
```

### Verify Installation

Restart Claude Desktop/Code, then check if skills are loaded:

```
/miniapp-audit-audit --help
```

## Quick Start

### Prerequisites

- Claude Desktop or Claude Code
- Node.js 18+ (for code analysis)
- WeChat Mini Program unpacking tool (e.g., [unwxapkg](https://github.com/wxappunpacker/unwxapkg))

### Basic Usage

**Standard audit (recommended)**:
```
/miniapp-audit-audit source_dir=/path/to/miniapp
```

**Quick scan**:
```
/miniapp-audit-audit source_dir=/path/to/miniapp mode=quick
```

**Deep analysis**:
```
/miniapp-audit-audit source_dir=/path/to/miniapp mode=deep
```

## Skills Overview

### Main Orchestrator

- **miniapp-audit-audit** - Main orchestrator coordinating the complete audit workflow

### Core Skills (all modes)

- **miniapp-audit-material-check** - Material integrity check and code quality assessment
- **miniapp-audit-attack-surface** - Attack surface analysis (APIs, permissions, domains, components)
- **miniapp-audit-secret-scan** - Credential leak scanning (keys, tokens, passwords)

### Standard Skills (standard/deep modes)

- **miniapp-audit-authz-analyzer** - Authorization analysis (privilege escalation risks)
- **miniapp-audit-payment-audit** - Payment security audit

### Deep Skills (deep mode only)

- **miniapp-audit-dataflow-tracer** - Data flow tracing (taint analysis)
- **miniapp-audit-privacy-compliance** - Privacy compliance check (PIPL, WeChat specifications)

### Auxiliary Skills

- **miniapp-audit-dynamic-tester** - Dynamic testing (requires test environment)
- **miniapp-audit-code-restorer** - Agent-level code restoration
- **miniapp-audit-report-builder** - Report generator

## Audit Modes

| Mode | Duration | Skills | Use Case |
|------|----------|--------|----------|
| **quick** | ~5 min | 4 | Quick screening, initial assessment |
| **standard** | ~15 min | 6 | Regular audit, compliance check |
| **deep** | ~30 min | 8 | Deep analysis, high-value targets |

## Code Restoration Feature

Addresses low-quality decompiled code issues (variable obfuscation, structural damage) with intelligent restoration:

**Capabilities**:
- Variable name inference based on data flow and context analysis (`a` → `userId`)
- Structure reconstruction (closure expansion, function extraction, nesting optimization)
- Comment generation for critical logic
- Complete variable renaming mapping

**Results**:
- Code quality score improvement: 42 → 78 (+36)
- Audit accuracy improvement: 30-50%
- Fully verifiable with complete mapping tables for manual review

**Usage**: Automatically prompts when `material-check` detects low-quality code.

## Output Structure

```
miniapp-audit-{timestamp}/
├── audit-report.md              # Chinese audit report
├── evidence/                    # All evidence files (JSON)
│   ├── material-check.json
│   ├── attack-surface.json
│   ├── secret-scan.json
│   ├── authz-findings.json
│   ├── payment-findings.json
│   ├── dataflow-analysis.json
│   └── privacy-compliance.json
├── restored/                    # Code restoration output (optional)
│   ├── pages/
│   ├── utils/
│   └── .original/
├── restoration-map.json         # Variable renaming map (optional)
├── restoration-report.md        # Restoration report (optional)
└── fuzzing/                     # Fuzzing tool output
    ├── endpoints.txt
    └── parameters.txt
```

## Configuration

### Shared Rules and Documentation

The `miniapp-audit-shared/` directory contains shared rules and documentation used by all skills:

- `rules/dataflow/` - Data flow analysis rules (source/sink/transform/guard patterns)
- `rules/privacy/` - Privacy compliance specifications (PIPL, WeChat guidelines)
- `docs/` - Test templates, algorithm documentation, severity standards

### Dynamic Testing Configuration

To enable dynamic testing, create `test-env.json`:

```json
{
  "base_url": "https://test-api.example.com",
  "auth": {
    "headers": {"Authorization": "Bearer test-token"}
  },
  "test_accounts": [
    {"username": "test_user", "password": "test_pass"}
  ]
}
```

## Architecture

```
.claude/skills/
├── miniapp-audit/           # 11 audit skills
│   ├── audit/              # Main orchestrator
│   ├── material-check/     # Material integrity
│   ├── attack-surface/     # Attack surface analysis
│   ├── secret-scan/        # Credential scanning
│   ├── authz-analyzer/     # Authorization analysis
│   ├── payment-audit/      # Payment security
│   ├── dataflow-tracer/    # Data flow tracing
│   ├── dynamic-tester/     # Dynamic testing
│   ├── privacy-compliance/ # Privacy compliance
│   ├── code-restorer/      # Code restoration
│   ├── report-builder/     # Report generation
│   └── shared/             # Schemas and rules
└── miniapp-audit-shared/   # Shared resources
    ├── rules/              # Detection rules
    └── docs/               # Documentation
```

## Design Principles

1. **Declarative/Instructional Style**: Skills tell agents what to do, not how to do it
2. **Single Source of Truth**: Rules and standards centrally maintained in shared directories
3. **Agent Parallel Orchestration**: Large-scale analysis tasks executed in parallel
4. **User-Friendly**: Interactive choices with transparent time and accuracy trade-offs

## Contributing

Issues and Pull Requests are welcome.

## License

MIT License

## Acknowledgments

- [Claude Agent SDK](https://docs.anthropic.com/claude/docs/agent-sdk) - Agent orchestration framework
- [unwxapkg](https://github.com/wxappunpacker/unwxapkg) - WeChat Mini Program unpacking tool
- WeChat Mini Program Security Community
