---
name: cyrus-skill-generator
description: Creates, updates and validates portable Agent Skills (SKILL.md folders with optional scripts, references and assets) that work in Claude Code, GitHub Copilot and OpenAI Codex. Use when the user asks to create, scaffold, write or generate a skill, to turn a workflow, prompt or runbook into a reusable skill, or to review, fix or port an existing SKILL.md for cross-tool compatibility and best practices.
license: MIT
compatibility: The bundled scripts need Python 3.8+ and use only the standard library. Targets Claude Code, GitHub Copilot and OpenAI Codex.
metadata:
  author: cyrus13
  version: "1.1.0"
  cyrus-platforms: "claude-code copilot codex"
  cyrus-invocation: "implicit"
---

# Cyrus Skill Generator

Builds skills that follow the open Agent Skills spec and load cleanly in Claude Code, GitHub Copilot and OpenAI Codex.

All paths below are relative to this skill's directory, meaning the folder that contains this SKILL.md. When you run a script, pass that directory's absolute path, for example `python3 <skill-dir>/scripts/validate_skill.py <target-skill-dir>`.

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

1. **Name.** Suggest one: `cyrus-` followed by a gerund or a clear action, for example `cyrus-reviewing-prs`. The rules: lowercase letters, digits and single hyphens; 64 characters or fewer; never `claude` or `anthropic`. Avoid vague words like `helper`, `utils` or `tools`.
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

- **Features.** Claude Code-only syntax and fields (argument substitution, skill-directory variables, `!` shell injection, `context: fork`, `paths`) are allowed only when Claude Code is the *only* target. If claude.ai / API is a target, use spec fields only.
- **Location.** In the cyrus-pal repo (the git root or the `origin` remote is named `cyrus-pal`), always use `skills/<name>/`. Anywhere else, ask whether this is a project skill or a personal one:

  | Targets | Project | Personal |
  | --- | --- | --- |
  | Include Codex or Copilot | `.agents/skills/<name>/`, plus a relative symlink `.claude/skills/<name>` → `../../.agents/skills/<name>` if Claude Code is also a target | `~/.agents/skills/<name>/`, plus a symlink at `~/.claude/skills/<name>` if Claude Code is also a target |
  | Claude Code only | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` |

- **Testing.** Test the skill on every target platform in step 7.

The details for each tool are in [references/compatibility.md](references/compatibility.md).

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
  --invocation implicit|explicit|background \
  --platforms claude-code,copilot,codex[,claude-api] \
  [--resources scripts,references,assets] [--openai-yaml]
```

What the script does:

- Adds the `cyrus-` prefix if it's missing.
- Writes the invocation fields for the chosen platforms.
- Records your answers in `metadata` as `cyrus-platforms` and `cyrus-invocation`. The validator uses these to tailor its checks.
- Creates SKILL.md from [assets/skill-template.md](assets/skill-template.md) and `evals/evals.json` from [assets/evals-template.json](assets/evals-template.json).
- Creates the Codex file `agents/openai.yaml` from [assets/openai-yaml-template.yaml](assets/openai-yaml-template.yaml) when an explicit skill targets Codex, or when you pass `--openai-yaml`.
- Exits with an error if the invocation mode isn't possible on a chosen platform, and never overwrites an existing folder.

Create any `.claude/skills` symlink from step 2 yourself afterwards.

### 5. Write SKILL.md and resources

Follow [references/authoring.md](references/authoring.md). The essentials:

- **Description:** third person. Say what the skill does and when to use it, and put the key trigger words first. Keep it to 1024 characters with no angle brackets. Every tool decides whether to load the skill from this field alone. For explicit skills it matters less, but it's still shown in menus.
- **Body:** imperative steps with explicit inputs and outputs. Give one default plus a way out instead of a menu of options. Include only what the agent wouldn't already know.
- **Resources:** link every resource file from SKILL.md, one level deep, using relative paths with forward slashes. For each script, say whether to run it or read it.
- **Frontmatter:** use spec fields plus the invocation fields from step 2. Add any other tool-specific field only when the skill needs that behaviour and every target supports it, and tell the user what it costs. The extensions table in [references/compatibility.md](references/compatibility.md) lists the trade-offs.
- **Keep the recorded answers current:** if the invocation mode or platforms change, update `cyrus-invocation` and `cyrus-platforms`.

### 6. Validate

```bash
python3 scripts/validate_skill.py <skill-dir>
```

Fix every ERROR. Fix every WARN, or explain to the user why you're keeping it. Re-run until the check passes, and don't move on before it does.

### 7. Evaluate on every target platform

Fill in `evals/evals.json` with trigger prompts and scenarios, then test as described in [references/evaluation.md](references/evaluation.md). On each target platform, run at least one realistic task in a fresh session. For implicit skills, also run a trigger test. If the skill triggers too rarely or too often, rewrite the description. Wherever the agent struggled, rewrite that part of the body. Report which platforms you actually tested.

### 8. Register and hand off

- **In cyrus-pal:** add a row to the skills index in the root `AGENTS.md`, then follow that file's working rules (a branch and a PR).
- **Tell the user:**
  - where the skill lives
  - how to invoke it on each target: `/<name>` in Claude Code and Copilot, `$<name>` in Codex
  - the invocation mode, and any tool-specific fields you used
  - the evaluation results, per platform

## Updating an existing skill

1. Run the validator. Use `--third-party` for skills that don't follow the cyrus conventions.
2. Read SKILL.md and every file it links to.
3. If `cyrus-invocation` or `cyrus-platforms` is missing, ask the questions in step 1 for the invocation mode and the platforms, then record the answers.
4. Apply steps 2-3 and 5-8 to the change.
5. Keep `name` unchanged, because renaming breaks existing slash commands. Bump `metadata.version`.
