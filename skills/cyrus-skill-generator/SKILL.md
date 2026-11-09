---
name: cyrus-skill-generator
description: Creates, updates and validates portable Agent Skills (SKILL.md folders with optional scripts, references and assets) that work in Claude Code, GitHub Copilot and OpenAI Codex. Use when the user asks to create, scaffold, write or generate a skill, to turn a workflow, prompt or runbook into a reusable skill, or to review, fix or port an existing SKILL.md for cross-tool compatibility and best practices.
license: MIT
compatibility: The bundled scripts need Python 3.8+ and use only the standard library. Targets Claude Code, GitHub Copilot and OpenAI Codex.
metadata:
  author: cyrus13
  version: "1.0.0"
  cyrus-platforms: "claude-code copilot codex"
  cyrus-invocation: "implicit"
---

# Cyrus Skill Generator

**Trace (do this first):** before anything else, print this exact line on its own: `[skill] cyrus-skill-generator v1.0.0 | started`. When the workflow ends, print `[skill] cyrus-skill-generator | finished`. If you stop early, print `[skill] cyrus-skill-generator | stopped: <reason>` instead.

Builds skills that follow the open Agent Skills spec and load cleanly in Claude Code, GitHub Copilot and OpenAI Codex.

All paths below are relative to this skill's directory, meaning the folder that contains this SKILL.md. When you run a script, pass that directory's absolute path, for example `python3 <skill-dir>/scripts/validate_skill.py <target-skill-dir>`.

Read a reference file only when a step below says so:

| File | Read it when |
| --- | --- |
| [references/authoring.md](references/authoring.md) | Before writing or rewriting a skill's description, body or resources (steps 3 and 5) |
| [references/evaluation.md](references/evaluation.md) | Before running the evals (step 7) |
| [references/compatibility.md](references/compatibility.md) | Only if you're adding a non-spec field or tool-specific syntax, placing a skill outside the locations in step 2, or working out why a tool doesn't load a skill |

## Workflow

Copy this checklist into your reply and tick items off as you go:

```
- [ ] 1. Ask the required questions (name, invocation, platforms)
- [ ] 2. Apply the answers (fields, platform features, location)
- [ ] 3. Plan the contents
- [ ] 4. Scaffold
- [ ] 5. Write SKILL.md and resources
- [ ] 6. Validate (repeat until clean)
- [ ] 7. Evaluate on every target platform
- [ ] 8. Register and hand off
```

### 1. Ask the required questions

Always ask these three questions in a single round, even if the conversation already hints at the answers. If it does, offer those answers as the defaults to confirm. Use the tool's structured question UI if it has one.

1. **Name.** Suggest one: `cyrus-` followed by a gerund or a clear action, for example `cyrus-reviewing-prs`. Avoid vague words like `helper`, `utils` or `tools`. The scripts enforce the format rules.
2. **Invocation.** Offer three options:
   - **Implicit** (the default): the agent loads the skill when a request matches its description, and the user can also invoke it by name.
   - **Explicit**: the skill runs only when the user invokes it by name. Recommend this for anything with side effects, such as deploying, sending, deleting or publishing.
   - **Background**: the agent loads it automatically, but it doesn't appear in the `/` menu. This is rare; use it only for reference knowledge.
3. **Target platforms** (multi-select): Claude Code, GitHub Copilot and OpenAI Codex, all three selected by default. claude.ai / Claude API upload is an extra option; only select it if the user asks, because it is the strictest target.

In the same round, ask for anything else that's still missing, again with a suggested default for each:

- What the skill should accomplish, and what "done" looks like.
- At least 3 realistic prompts that should trigger it, and 1-2 near misses that should not.
- The inputs it needs, the CLIs or MCP servers it relies on, and any steps that must never happen.

### 2. Apply the answers

**Invocation** maps to different settings in each tool. `init_skill.py` writes them for you:

| Mode | Claude Code and Copilot | Codex | claude.ai / API |
| --- | --- | --- | --- |
| Implicit | No extra fields | No extra fields | Supported |
| Explicit | `disable-model-invocation: true` | `agents/openai.yaml` with `policy.allow_implicit_invocation: false` | Not possible. Ask the user to drop this target or choose implicit |
| Background | `user-invocable: false` | No equivalent (the skill stays visible). Tell the user | Not possible |

**Platforms** change three things:

- **Features.** Use only spec fields and portable syntax, unless every target supports the extra feature. Claude Code-only features are fine when Claude Code is the only target. If claude.ai / API is a target, use spec fields only.
- **Location.** In the cyrus-pal repo (the git root or the `origin` remote is named `cyrus-pal`), always use `skills/<name>/`. Anywhere else, ask whether this is a project skill or a personal one:

  | Targets | Project | Personal |
  | --- | --- | --- |
  | Include Codex or Copilot | `.agents/skills/<name>/`, plus a relative symlink `.claude/skills/<name>` → `../../.agents/skills/<name>` if Claude Code is also a target | `~/.agents/skills/<name>/`, plus a symlink at `~/.claude/skills/<name>` if Claude Code is also a target |
  | Claude Code only | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` |

- **Testing.** Test the skill on every target platform in step 7.

### 3. Plan the contents

Read references/authoring.md now if you haven't yet. Decide what goes in the description, the body, `references/`, `scripts/` and `assets/`, using its "Progressive disclosure" table. Make the skill instructions-only unless a script is clearly needed.

### 4. Scaffold

```bash
python3 scripts/init_skill.py <name> --path <parent-dir> --description "<description>" \
  --invocation implicit|explicit|background \
  --platforms claude-code,copilot,codex[,claude-api] \
  [--resources scripts,references,assets] [--openai-yaml]
```

The script does the following:

- Adds the `cyrus-` prefix.
- Writes the invocation settings from step 2.
- Records the answers in `metadata` as `cyrus-platforms` and `cyrus-invocation`.
- Fills in [assets/skill-template.md](assets/skill-template.md), [assets/evals-template.json](assets/evals-template.json) and, when Codex needs it, [assets/openai-yaml-template.yaml](assets/openai-yaml-template.yaml).

It never overwrites an existing folder. Create any `.claude/skills` symlink from step 2 yourself afterwards.

### 5. Write SKILL.md and resources

Fill in every placeholder in the scaffold, following references/authoring.md. Two things that guide doesn't cover:

- **Frontmatter:** spec fields plus the invocation settings from step 2. If you add any other field, tell the user what it costs.
- **Recorded answers:** if the invocation mode or platforms change, update `cyrus-invocation` and `cyrus-platforms`.

### 6. Validate

```bash
python3 scripts/validate_skill.py <skill-dir>
```

Fix every ERROR. Fix every WARN, or explain to the user why you're keeping it. Re-run until the check passes, and don't move on before it does.

### 7. Evaluate on every target platform

Read references/evaluation.md and follow it. You run the tests in headless sessions, after asking the user once. The user reviews the results and does a manual checklist for whatever you can't or mustn't run, such as side effects or platforms without a CLI.

### 8. Register and hand off

- **In cyrus-pal:** add a row to the skills index in the root `AGENTS.md`, then follow that file's working rules (a branch and a PR).
- **Tell the user:**
  - where the skill lives
  - how to invoke it on each target: `/<name>` in Claude Code and Copilot, `$<name>` (or the `/skills` picker) in Codex
  - the invocation mode, and any tool-specific fields you used
  - the evaluation results, per platform

## Updating an existing skill

1. Run the validator. Use `--third-party` for skills that don't follow the cyrus conventions.
2. Read SKILL.md and every file it links to.
3. If `cyrus-invocation` or `cyrus-platforms` is missing, ask the questions in step 1 for the invocation mode and the platforms, then record the answers.
4. Apply steps 2-3 and 5-8 to the change.
5. Keep `name` unchanged, because renaming breaks existing slash commands. Bump `metadata.version` and the trace line together, as described in "Trace logging" in references/authoring.md. If the skill has no trace block yet, add one.
