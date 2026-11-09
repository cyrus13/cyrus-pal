# cyrus-pal

A personal collection of tools for agentic development: reusable building blocks that make AI coding agents (Claude Code, GitHub Copilot and OpenAI Codex) more capable and consistent.

## Repository layout

```
cyrus-pal/
├── skills/        # Agent skills, one folder per skill
├── AGENTS.md      # Map for AI agents: routes to skills and other files
├── CLAUDE.md      # Claude Code entry point (imports AGENTS.md)
├── LICENSE
└── README.md
```

More tool types (for example commands, hooks or agent definitions) may be added as top-level folders over time.

## Skills

The [`skills/`](skills/) folder contains agent skills. A skill is a packaged set of instructions, plus optional scripts and reference files, that an agent loads when a task matches its description.

Skills follow the open [Agent Skills](https://agentskills.io/specification) format, so the same folder works in Claude Code, GitHub Copilot and OpenAI Codex. Each skill lives in its own folder and has a `SKILL.md` entry point:

```
skills/
└── cyrus-my-skill/
    ├── SKILL.md       # Required: frontmatter + instructions
    ├── scripts/       # Optional: code the agent runs
    ├── references/    # Optional: extra docs loaded on demand
    ├── assets/        # Optional: templates and static files
    ├── agents/        # Optional: openai.yaml (Codex UI and invocation policy)
    └── evals/         # Optional: evals.json (trigger tests and scenarios)
```

A minimal `SKILL.md`:

```markdown
---
name: cyrus-my-skill
description: One or two sentences on what the skill does. Use when the user asks to ...
---

# My Skill

Step-by-step instructions for the agent.
```

### Available skills

| Skill | What it does |
| --- | --- |
| [`cyrus-skill-generator`](skills/cyrus-skill-generator/SKILL.md) | Creates, updates and validates portable skills for Claude Code, Copilot and Codex. Includes scaffolding (`init_skill.py`) and a cross-tool validator (`validate_skill.py`). |

### Creating a skill

Use the generator: in Claude Code or Copilot type `/cyrus-skill-generator`, and in Codex type `$cyrus-skill-generator`. You can also just describe the skill you want, and the agent will load the generator by itself. It always asks for three things:

- the **name** (prefixed with `cyrus-`)
- the **invocation** mode: *implicit* (the agent loads it when relevant), *explicit* (only when you invoke it by name) or *background* (the agent loads it, but it's hidden from menus)
- the **target platforms**: Claude Code, Copilot and/or Codex, plus claude.ai / API upload

It then writes the right settings for each platform and records your choices in the skill's `metadata` as `cyrus-invocation` and `cyrus-platforms`, so the validator can tailor its checks.

Every cyrus skill prints **trace lines**, so the console shows which skill (and which version) is running:

```
[skill] cyrus-skill-generator v1.2.0 | started
[skill] cyrus-skill-generator | scripts/validate_skill.py   # each script, on stderr
[skill] cyrus-skill-generator | finished
```

The generator also tests the skills it creates. It runs each one in a fresh headless session on every target platform whose CLI you have installed, and detects whether the skill triggered from its trace line. It asks before these runs, and leaves anything with side effects, or any platform it can't run, to you as a short checklist.

To validate a skill by hand:

```bash
python3 skills/cyrus-skill-generator/scripts/validate_skill.py skills/<skill-name>
```

### Installing the skills

Each tool reads skills from a different folder, so symlink each skill into the folders for the tools you use. Symlinks keep the installed copy in sync with this repo.

| Tool | Personal folder | Project folder |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` |
| GitHub Copilot | `~/.agents/skills/` or `~/.copilot/skills/` | `.agents/skills/`, `.github/skills/` or `.claude/skills/` |

```bash
# From the root of this repo. Install one skill for all three tools (personal scope):
mkdir -p ~/.claude/skills ~/.agents/skills
ln -s "$(pwd)/skills/cyrus-skill-generator" ~/.claude/skills/cyrus-skill-generator   # Claude Code
ln -s "$(pwd)/skills/cyrus-skill-generator" ~/.agents/skills/cyrus-skill-generator   # Codex + Copilot

# Uninstall: remove the symlinks (this doesn't touch the repo copy)
rm ~/.claude/skills/cyrus-skill-generator ~/.agents/skills/cyrus-skill-generator
```

Some Copilot surfaces read both `~/.agents/skills/` and `~/.claude/skills/`, so a skill may show up twice. The duplicate is harmless. Reload or restart the tool if a new skill doesn't appear: run `/skills reload` in Copilot CLI, or restart Codex.

> **Planned:** a cross-platform installer (for example an `npx` command) that installs skills into every tool's folder in one step. This still needs research.

## Contributing

- Branch off `main` and open a pull request against `main`. Don't push directly to it.
- Name every skill with the `cyrus-` prefix, and keep each skill self-contained in its own folder under `skills/`.
- Run `validate_skill.py` on a skill before opening a PR.
- When you add, rename or remove a skill, update the skills index in [`AGENTS.md`](AGENTS.md).
- Write a clear `description` in each skill's frontmatter, since agents use it to decide when to load the skill.

## License

[MIT](LICENSE)
