#!/usr/bin/env python3
"""Scaffold a new cross-tool Agent Skill folder.

Usage:
  python3 init_skill.py <name> --path <parent-dir> [--description TEXT]
                        [--resources scripts,references,assets] [--openai-yaml]

The name is lowercased, hyphenated and given the "cyrus-" prefix if it lacks it.
Creates <parent-dir>/<name>/ with:
  SKILL.md           from assets/skill-template.md
  evals/evals.json   from assets/evals-template.json
  agents/openai.yaml from assets/openai-yaml-template.yaml (with --openai-yaml)
  <resource>/.gitkeep for each --resources entry
Refuses to touch an existing folder. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PREFIX = "cyrus-"
MAX_NAME_LEN = 64  # Agent Skills spec limit
MAX_DESCRIPTION_LEN = 1024  # Agent Skills spec limit
RESERVED_WORDS = ("claude", "anthropic")  # rejected by claude.ai / Claude API
RESOURCE_DIRS = ("scripts", "references", "assets")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

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


def check_name(name):
    if not NAME_RE.match(name):
        return "name must be lowercase letters, digits and single hyphens"
    if len(name) > MAX_NAME_LEN:
        return f"name is {len(name)} chars; the limit is {MAX_NAME_LEN}"
    for word in RESERVED_WORDS:
        if word in name:
            return f"name must not contain the reserved word '{word}'"
    if name == PREFIX.rstrip("-"):
        return "name needs words after the prefix, e.g. cyrus-reviewing-prs"
    return None


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
    parser.add_argument("--resources", default="", help="comma-separated: scripts,references,assets")
    parser.add_argument("--openai-yaml", action="store_true", help="also create agents/openai.yaml for Codex")
    args = parser.parse_args()

    name = normalise_name(args.name)
    problem = check_name(name)
    if problem:
        sys.exit(f"error: '{name}': {problem}")

    resources = [r.strip() for r in args.resources.split(",") if r.strip()]
    unknown = [r for r in resources if r not in RESOURCE_DIRS]
    if unknown:
        sys.exit(f"error: unknown resource dir(s) {unknown}; choose from {list(RESOURCE_DIRS)}")

    description = (args.description or PLACEHOLDER_DESCRIPTION).strip()
    if len(description) > MAX_DESCRIPTION_LEN:
        sys.exit(f"error: description is {len(description)} chars; the limit is {MAX_DESCRIPTION_LEN}")
    if "<" in description and args.description:
        sys.exit("error: description must not contain angle brackets (claude.ai rejects XML tags)")

    parent = Path(args.path).expanduser()
    target = parent / name
    if target.exists() or target.is_symlink():
        sys.exit(f"error: {target} already exists; not overwriting. Edit it instead.")

    values = {
        "name": name,
        "title": title_from(name),
        # A JSON string is a valid YAML double-quoted scalar, so this is always safe YAML.
        "description": json.dumps(description, ensure_ascii=False),
    }

    files = {
        target / "SKILL.md": render("skill-template.md", values),
        target / "evals" / "evals.json": render("evals-template.json", values),
    }
    if args.openai_yaml:
        files[target / "agents" / "openai.yaml"] = render("openai-yaml-template.yaml", values)
    for resource in resources:
        files[target / resource / ".gitkeep"] = ""

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    print(f"Created {target}")
    for path in sorted(files):
        print(f"  {path.relative_to(target)}")
    print("\nNext: replace every TODO, link each resource from SKILL.md, then run:")
    print(f"  python3 {Path(__file__).resolve().parent / 'validate_skill.py'} {target}")


if __name__ == "__main__":
    main()
