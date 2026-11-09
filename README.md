# cyrus-pal

A personal collection of tools for agentic development: reusable building blocks that make AI coding agents (such as Claude Code) more capable and consistent.

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

Each skill lives in its own folder and has a `SKILL.md` entry point:

```
skills/
└── my-skill/
    ├── SKILL.md       # Required: frontmatter + instructions
    ├── scripts/       # Optional: helper scripts the skill runs
    └── references/    # Optional: extra docs loaded on demand
```

A minimal `SKILL.md`:

```markdown
---
name: my-skill
description: One or two sentences on what the skill does and when the agent should use it.
---

# My Skill

Step-by-step instructions for the agent.
```

### Using the skills with Claude Code

To make a skill available to Claude Code, link or copy its folder into a skills directory:

- **Personal (all projects):** `~/.claude/skills/`
- **Per project:** `<project>/.claude/skills/`

```bash
# Example: symlink one skill for personal use
ln -s "$(pwd)/skills/my-skill" ~/.claude/skills/my-skill
```

Symlinking keeps the installed skill in sync with this repo.

## Contributing

- Branch off `main` and open a pull request against `main`. Don't push directly to it.
- Keep each skill self-contained in its own folder under `skills/`.
- When you add, rename or remove a skill, update the skills index in [`AGENTS.md`](AGENTS.md).
- Write a clear `description` in each skill's frontmatter, since agents use it to decide when to load the skill.

## License

[MIT](LICENSE)
