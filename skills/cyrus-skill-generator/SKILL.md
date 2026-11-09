---
name: cyrus-skill-generator
description: Creates, updates and validates portable Agent Skills (SKILL.md folders with optional scripts, references and assets) that work in Claude Code, GitHub Copilot and OpenAI Codex. Use when the user asks to create, scaffold, write or generate a skill, to turn a workflow, prompt or runbook into a reusable skill, or to review, fix or port an existing SKILL.md for cross-tool compatibility and best practices.
license: MIT
compatibility: The bundled scripts need Python 3.8+ and use only the standard library. Targets Claude Code, GitHub Copilot and OpenAI Codex.
metadata:
  author: cyrus13
  version: "1.0.0"
---

# Cyrus Skill Generator

Builds skills that follow the open Agent Skills spec and load cleanly in Claude Code, GitHub Copilot and OpenAI Codex.

All paths below are relative to this skill's directory, meaning the folder that contains this SKILL.md. When you run a script, pass that directory's absolute path, for example `python3 <skill-dir>/scripts/validate_skill.py <target-skill-dir>`.

## Workflow

Copy this checklist into your reply and tick items off as you go:

```
- [ ] 1. Capture intent
- [ ] 2. Name and place the skill
- [ ] 3. Plan the contents
- [ ] 4. Scaffold
- [ ] 5. Write SKILL.md and resources
- [ ] 6. Validate (repeat until clean)
- [ ] 7. Evaluate
- [ ] 8. Register and hand off
```

### 1. Capture intent

Get what you can from the conversation first. A workflow the user just walked through is the best source. Then ask only for what is still missing, in one round, and suggest a default for each question:

- What the skill should accomplish, and what "done" looks like (outputs, files, side effects).
- At least 3 realistic prompts that should trigger it, and 1-2 near misses that should not.
- The inputs it needs, the CLIs or MCP servers it relies on, and any steps that are fragile or must never happen.

### 2. Name and place the skill

**Name.** Always start with `cyrus-`, followed by lowercase words joined by hyphens. Keep it to 64 characters or fewer, with no `--`, and never include `claude` or `anthropic`. Prefer a gerund or a clear action (`cyrus-reviewing-prs`, `cyrus-writing-release-notes`). Avoid vague words like `helper`, `utils` or `tools`. The init script adds the prefix if it's missing.

**Location.** Decide this before you scaffold:

- **In the cyrus-pal repo** (the git root or the `origin` remote is named `cyrus-pal`): use `skills/<name>/`.
- **Anywhere else:** ask the user which of these they want:
  - **cyrus-pal:** versioned centrally. Only offer this if they have a local checkout.
  - **Project:** a real folder in `.agents/skills/<name>/` (read by Codex and Copilot), plus a relative symlink `.claude/skills/<name>` pointing to `../../.agents/skills/<name>` (read by Claude Code).
  - **Personal:** `~/.agents/skills/<name>/`, plus a symlink at `~/.claude/skills/<name>`.

[references/compatibility.md](references/compatibility.md) lists where each tool looks for skills.

### 3. Plan the contents

Keep SKILL.md as a short table of contents and move detail into files that load only when needed:

| Content | Where it goes | When it loads |
| --- | --- | --- |
| What the skill does, when to use it, trigger words | `description` | Always, in every session |
| Core workflow, defaults, gotchas | SKILL.md body (under 500 lines; aim for under 200) | When the skill triggers |
| Detailed docs, schemas, domain variants, long examples | `references/*.md` | Only when SKILL.md says to read them |
| Steps that must be exact, fragile steps, validation | `scripts/` | Run, not read; only the output uses context |
| Templates, boilerplate, images, data files | `assets/` | Used in the output, rarely read |

Make the skill instructions-only unless you have a reason not to. Add a script when the agent would otherwise rewrite the same code each time, or when correctness has to be guaranteed. The riskier a step, the more exactly it should be scripted or spelled out. See [references/authoring.md](references/authoring.md).

### 4. Scaffold

```bash
python3 scripts/init_skill.py <name> --path <parent-dir> --description "<description>" \
  [--resources scripts,references,assets] [--openai-yaml]
```

The script adds the `cyrus-` prefix if needed. It creates SKILL.md from [assets/skill-template.md](assets/skill-template.md) and `evals/evals.json` from [assets/evals-template.json](assets/evals-template.json). With `--openai-yaml`, it also creates the Codex file `agents/openai.yaml` from [assets/openai-yaml-template.yaml](assets/openai-yaml-template.yaml). It never overwrites an existing folder. For the project and personal layouts, create the `.claude/skills` symlink yourself afterwards.

### 5. Write SKILL.md and resources

Follow [references/authoring.md](references/authoring.md). The essentials:

- **Description:** third person. Say what the skill does and when to use it, and put the key trigger words first. Keep it to 1024 characters with no angle brackets. Every tool decides whether to load the skill from this field alone.
- **Body:** imperative steps with explicit inputs and outputs. Give one default plus a way out instead of a menu of options. Include only what the agent wouldn't already know.
- **Resources:** link every resource file from SKILL.md, one level deep, using relative paths with forward slashes. For each script, say whether to run it or read it.
- **Frontmatter:** use only the spec fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`). Add a tool-specific field only when the skill needs that behaviour, and tell the user what it costs. The extensions table in [references/compatibility.md](references/compatibility.md) lists the trade-offs.
- **Portable body text:** avoid syntax that only one tool understands, such as argument placeholders, skill-directory variables or shell injection. Describe paths as relative to the skill's directory instead.

### 6. Validate

```bash
python3 scripts/validate_skill.py <skill-dir>
```

Fix every ERROR. Fix every WARN, or explain to the user why you're keeping it. Re-run until the check passes, and don't move on before it does.

### 7. Evaluate

Fill in `evals/evals.json` with trigger prompts and scenarios, then test as described in [references/evaluation.md](references/evaluation.md). At minimum, run one trigger test in a fresh session and one realistic task in the user's main tool. If the skill triggers too rarely or too often, rewrite the description. Wherever the agent struggled, rewrite that part of the body.

### 8. Register and hand off

- **In cyrus-pal:** add a row to the skills index in the root `AGENTS.md`, then follow that file's working rules (a branch and a PR).
- **Tell the user:**
  - where the skill lives
  - how to invoke it: `/<name>` in Claude Code and Copilot, `$<name>` in Codex
  - any tool-specific fields you used
  - the evaluation results

## Updating an existing skill

1. Run the validator. Use `--no-prefix-check` for third-party skills that don't follow the `cyrus-` naming.
2. Read SKILL.md and every file it links to.
3. Apply steps 3 and 5-8 to the change.
4. Keep `name` unchanged, because renaming breaks existing slash commands. Bump `metadata.version`.
