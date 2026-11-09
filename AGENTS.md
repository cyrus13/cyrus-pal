# AGENTS.md

Entry point for AI agents working in this repo. Use it as a map. Details live in the files linked below, so open the one that matches your task instead of guessing.

## What this repo is

`cyrus-pal` is a collection of tools for agentic development. Right now it holds **skills**. Other tool types may be added later as new top-level folders. The human-facing overview is in [README.md](README.md).

## Where to look

| If you need to... | Go to |
| --- | --- |
| Understand the repo layout and the skill format | [README.md](README.md) |
| Use or change an existing skill | `skills/<skill-name>/SKILL.md` (see the index below) |
| Add a new skill | [README.md#skills](README.md#skills), then add a row to the index below |

## Skills index

Each skill is self-contained in `skills/<skill-name>/`, and `SKILL.md` is its entry point. Read the skill's `SKILL.md` before using it. Open its `scripts/` or `references/` files only when the `SKILL.md` tells you to.

| Skill | Use when | Entry point |
| --- | --- | --- |
| _(none yet)_ | | |

Keep this table in sync with `skills/`. Add, rename or remove a row in the same change that adds, renames or removes a skill folder.

## Working rules

- **Never commit straight to `main`.** Make a branch, push it, and open a PR against `main` (`gh pr create --base main`).
- **One skill, one folder.** Don't share files across skill folders. If several skills need the same thing, raise it in the PR.
- **Descriptions matter.** A skill's frontmatter `description` decides when agents load it. Make it say what the skill does and when to use it.
- **Update the maps.** When you add a new kind of tool (a new top-level folder), add it to "Where to look" here and to the layout section in [README.md](README.md).
