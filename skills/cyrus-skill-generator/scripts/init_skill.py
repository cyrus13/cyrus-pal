#!/usr/bin/env python3
"""Scaffold a new cross-tool Agent Skill folder.

Usage:
  python3 init_skill.py <name> --path <parent-dir> [--description TEXT]
                        [--invocation implicit|explicit|background]
                        [--platforms claude-code,copilot,codex[,claude-api]]
                        [--resources scripts,references,assets] [--openai-yaml]

The name is lowercased, hyphenated and given the "cyrus-" prefix if it lacks it.
The invocation fields each platform needs come from skill_rules.InvocationPlan,
the same rules validate_skill.py checks. Both answers are recorded in metadata
(cyrus-platforms, cyrus-invocation).

Creates <parent-dir>/<name>/ from the templates in ../assets/, adding
agents/openai.yaml when Codex needs it (or with --openai-yaml). Refuses to touch
an existing folder. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
sys.path.insert(0, str(Path(__file__).resolve().parent))  # find skill_rules.py even under python -I
from skill_rules import (  # noqa: E402  (shared rules: skill_rules.py)
    DEFAULT_PLATFORMS, INVOCATIONS, PLATFORMS, PREFIX, InvocationPlan, description_problems, name_problems,
)

RESOURCE_DIRS = ("scripts", "references", "assets")
TRACE = "[skill] cyrus-skill-generator | scripts/init_skill.py"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
PLACEHOLDER_DESCRIPTION = (
    "TODO: Third-person summary of what this skill does. "
    "Use when the user asks to <concrete triggers>."
)


def normalise_name(raw):
    name = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    if not name.startswith(PREFIX):
        name = PREFIX + name
    return name


def parse_platforms(raw):
    platforms = [p.strip() for p in raw.split(",") if p.strip()]
    unknown = [p for p in platforms if p not in PLATFORMS]
    if unknown or not platforms:
        sys.exit(f"error: unknown or empty platform list {unknown or raw!r}; choose from {list(PLATFORMS)}")
    return [p for p in PLATFORMS if p in platforms]  # stable, de-duplicated order


def title_from(name):
    return " ".join(part.capitalize() for part in name.split("-"))


def render(template_name, values):
    path = ASSETS / template_name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(f"error: cannot read template {path}: {exc}")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Agent Skill.")
    parser.add_argument("name", help="skill name; 'cyrus-' is prepended if missing")
    parser.add_argument("--path", required=True, help="parent directory, e.g. skills or .agents/skills")
    parser.add_argument("--description", help="frontmatter description (third person, what + when)")
    parser.add_argument("--invocation", choices=INVOCATIONS, default="implicit",
                        help="implicit (auto + by name), explicit (by name only), background (auto, hidden)")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS),
                        help=f"comma-separated from {','.join(PLATFORMS)} (default: {','.join(DEFAULT_PLATFORMS)})")
    parser.add_argument("--resources", default="", help="comma-separated: scripts,references,assets")
    parser.add_argument("--openai-yaml", action="store_true", help="always create agents/openai.yaml for Codex")
    args = parser.parse_args()
    print(TRACE, file=sys.stderr)

    name = normalise_name(args.name)
    problems = name_problems(name)
    if problems:
        sys.exit("error: " + "; ".join(problems))

    platforms = parse_platforms(args.platforms)
    plan = InvocationPlan(args.invocation, platforms)
    if plan.error:
        sys.exit(f"error: {plan.error}")
    fields, need_openai_yaml, notes = plan.frontmatter_fields(), plan.codex_implicit_off, list(plan.notes)
    if args.openai_yaml and "codex" not in platforms:
        notes.append("agents/openai.yaml is only read by Codex, which is not a target platform.")

    resources = [r.strip() for r in args.resources.split(",") if r.strip()]
    unknown = [r for r in resources if r not in RESOURCE_DIRS]
    if unknown:
        sys.exit(f"error: unknown resource dir(s) {unknown}; choose from {list(RESOURCE_DIRS)}")

    description = (args.description or PLACEHOLDER_DESCRIPTION).strip()
    if args.description:
        problems = description_problems(description)
        if problems:
            sys.exit("error: " + "; ".join(problems))

    parent = Path(args.path).expanduser()
    target = parent / name
    if target.exists() or target.is_symlink():
        sys.exit(f"error: {target} already exists; not overwriting. Edit it instead.")

    values = {
        "name": name,
        "title": title_from(name),
        # A JSON string is a valid YAML double-quoted scalar, so this is always safe YAML.
        "description": json.dumps(description, ensure_ascii=False),
        "invocation_fields": "".join(f + "\n" for f in fields),
        "platforms": " ".join(platforms),
        "invocation": args.invocation,
        "allow_implicit": "false" if args.invocation == "explicit" else "true",
    }

    files = {
        target / "SKILL.md": render("skill-template.md", values),
        target / "evals" / "evals.json": render("evals-template.json", values),
    }
    if need_openai_yaml or args.openai_yaml:
        files[target / "agents" / "openai.yaml"] = render("openai-yaml-template.yaml", values)
    for resource in resources:
        files[target / resource / ".gitkeep"] = ""

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    print(f"Created {target}")
    print(f"  platforms: {', '.join(platforms)} | invocation: {args.invocation}")
    for path in sorted(files):
        print(f"  {path.relative_to(target)}")
    for note in notes:
        print(f"note: {note}")
    print("\nNext: replace every TODO, link each resource from SKILL.md, then run:")
    print(f"  python3 {Path(__file__).resolve().parent / 'validate_skill.py'} {target}")


if __name__ == "__main__":
    main()
