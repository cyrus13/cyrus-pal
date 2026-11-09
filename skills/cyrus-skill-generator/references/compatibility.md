# Cross-tool compatibility

Verified against official docs on 2026-11-09. If a tool's behaviour seems to differ from what's written here, re-check the sources listed at the end.

## Contents

- [The shared baseline](#the-shared-baseline)
- [Discovery locations](#discovery-locations)
- [Frontmatter fields](#frontmatter-fields)
- [Tool-specific extensions](#tool-specific-extensions)
- [Body syntax](#body-syntax)
- [Codex sidecar: agents/openai.yaml](#codex-sidecar-agentsopenaiyaml)
- [Context budgets](#context-budgets)
- [Sources](#sources)

## The shared baseline

All three tools follow the open Agent Skills spec (agentskills.io):

- A skill is a folder. Its name matches the skill's `name`, and it contains a `SKILL.md`. The file's first line must be `---`, followed by YAML frontmatter and then a Markdown body.
- Optional subfolders: `scripts/` (executable code), `references/` (docs loaded on demand) and `assets/` (templates and static files).
- Loading happens in three stages:
  1. At startup the tool reads only `name` and `description`, about 100 tokens per skill.
  2. When the skill triggers, it reads the SKILL.md body. Keep the body under 5000 tokens and 500 lines.
  3. It reads resource files only when the body points to them.

A skill that uses only this baseline works in all three tools, and also in claude.ai and the Claude API.

## Discovery locations

| Tool | Project | Personal |
| --- | --- | --- |
| Claude Code | `.claude/skills/` in the start directory and each parent up to the repo root. Nested `<subdir>/.claude/skills/` loads the first time Claude touches a file in that subdirectory | `~/.claude/skills/` |
| GitHub Copilot (cloud agent, CLI, VS Code) | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | `~/.copilot/skills/`, `~/.agents/skills/` (VS Code local sessions also read `~/.claude/skills/`) |
| OpenAI Codex | `.agents/skills/` in the start directory and each parent up to the repo root | `~/.agents/skills/` (admins: `/etc/codex/skills`) |

**Covering all three from one copy:** the layout in SKILL.md step 2 works because Claude Code and Codex both follow symlinked skill folders, and a relative symlink (`../../.agents/skills/<name>`) still works after someone clones the repo.

**Caveats:**
- Copilot also reads `.claude/skills/`, so it may list the same skill twice. The duplicate is harmless.
- On Windows, git may check symlinks out as plain text files unless `core.symlinks` is enabled.

**Same name in two locations:**
- Claude Code: enterprise beats personal, and personal beats project.
- Codex: shows both entries and doesn't merge them.
- VS Code: shows both entries.

The `cyrus-` prefix avoids most clashes.

**Reloading:**
- Claude Code: picks up edits live. After creating a new top-level skills folder, run `/reload-skills`.
- Copilot CLI: run `/skills reload`.
- Codex: picks up changes automatically; restart it if a change doesn't show.

## Frontmatter fields

These are the spec fields. Use only these by default.

| Field | Rules (strictest across tools) | Claude Code | Copilot | Codex |
| --- | --- | --- | --- | --- |
| `name` | Required. 1-64 chars of `a-z`, `0-9` and `-`. No leading, trailing or double hyphen. Must match the folder name. claude.ai and the API also reject names containing `claude` or `anthropic` | Optional (defaults to the folder name) and used as the `/command` | Required. **An invalid name makes the skill silently fail to load** | Required |
| `description` | Required. 1-1024 chars, no angle brackets (claude.ai and the API reject XML tags) | Truncated at 1536 chars, together with `when_to_use` | Required, max 1024 | Required. Shortened when the skill list is over budget |
| `license` | Short licence name or bundled file name | Accepted, has no effect | Supported | Not documented |
| `compatibility` | 1-500 chars of environment requirements. Leave it out unless it's needed | Accepted, has no effect | Not documented | Not documented |
| `metadata` | Map of string keys to string values. Quote values that look like numbers (`version: "1.0"`) | Ignored | `gh skill install` writes provenance here | Not documented |
| `allowed-tools` | Experimental. Space-separated string of pre-approved tools | Pre-approves those tools for the turn (`Bash(git add *)`) | Pre-approves those tools (`shell`). GitHub warns to do this only for trusted scripts | Not documented |

Unknown keys are ignored by Claude Code, but **rejected by claude.ai uploads and the Claude API** with an error like "Unexpected key(s) in SKILL.md frontmatter".

Claude Code loads a skill with malformed YAML but sets none of its fields, so the skill quietly loses its description. Keep the YAML simple: plain `key: value` pairs, quote any value that contains `: `, and use block scalars (`>`) for long text.

## Tool-specific extensions

Use one of these only when the skill truly needs the behaviour. Each one makes the skill unusable on claude.ai and the API.

| Field | What it does | Supported by | Portable alternative |
| --- | --- | --- | --- |
| `disable-model-invocation: true` | User-only: the agent never auto-loads the skill | Claude Code, VS Code Copilot | Codex reads `agents/openai.yaml` instead (below) |
| `user-invocable: false` | Hides the skill from the `/` menu; the agent can still load it | Claude Code, VS Code Copilot | None. Usually not worth it |
| `argument-hint` | Autocomplete hint text, for example `[issue-number]` | Claude Code, VS Code Copilot | Describe the expected input in the body |
| `context: fork` | Runs the skill in an isolated subagent | Claude Code, VS Code Copilot (experimental; needs `github.copilot.chat.skillTool.enabled`) | None |
| `when_to_use` | Extra trigger text appended to the description | Claude Code only | Put it in `description` |
| `paths` | Auto-loads only when matching files are touched | Claude Code only | Name the file types in `description` |
| `arguments`, `disallowed-tools`, `model`, `effort`, `agent`, `background`, `hooks`, `shell` | Claude Code runtime controls | Claude Code only | None |

## Body syntax

- **Claude Code only:**
  - `$ARGUMENTS`, `$0`, `$name`
  - `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`
  - inline `` !`command` `` and fenced ```` ```! ```` blocks (they run before the skill loads)
  - `ultrathink`

  Other tools see these as literal text. If a skill needs one of them, also write the instruction in plain words. For example, add "the user's request is the argument" next to `$ARGUMENTS`.
- **Copilot only:** `#file:` references. Use normal Markdown links instead.

## Codex sidecar: agents/openai.yaml

This file is optional, and Codex is the only tool that reads it. It controls UI metadata (for the ChatGPT and Codex apps), the invocation policy and dependencies. Documented keys:

```yaml
interface:
  display_name: "User-facing name"
  short_description: "User-facing description"
  icon_small: "./assets/small-logo.svg"
  icon_large: "./assets/large-logo.png"
  brand_color: "#3B82F6"
  default_prompt: "Surrounding prompt used with the skill"
policy:
  allow_implicit_invocation: false   # default true; explicit $name still works
dependencies:
  tools:
    - type: "mcp"
      value: "openaiDeveloperDocs"
      description: "OpenAI Docs MCP server"
      transport: "streamable_http"
      url: "https://developers.openai.com/mcp"
```

Add it when a skill should be user-only, or when it depends on an MCP server.

## Context budgets

- **Claude Code:** the skill list gets about 1% of the context window, capped at 1536 chars per entry. When over budget, it drops descriptions of the least-used skills first. After compaction it re-attaches the first 5000 tokens of each invoked skill, with 25000 tokens shared across all skills.
- **Codex:** the skill list gets 2% of the context window (8000 chars when the window size is unknown). It shortens descriptions first and may leave skills out.

## Sources

- Agent Skills spec: https://agentskills.io/specification
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- GitHub Copilot skills: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- VS Code agent skills: https://code.visualstudio.com/docs/copilot/customization/agent-skills
- Codex skills: https://developers.openai.com/codex/skills
