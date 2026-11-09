#!/usr/bin/env python3
"""Scaffold a new cross-tool Agent Skill folder.

Usage:
  python3 init_skill.py <name> --path <parent-dir> [--description TEXT]
                        [--invocation implicit|explicit|background]
                        [--platforms claude-code,copilot,codex[,claude-api]]
                        [--resources scripts,references,assets] [--openai-yaml]

The name is lowercased, hyphenated and given the "cyrus-" prefix if it lacks it.
Invocation and platforms decide which fields get written:
  explicit   -> disable-model-invocation: true (Claude Code, Copilot) and
                agents/openai.yaml policy.allow_implicit_invocation: false (Codex)
  background -> user-invocable: false (Claude Code, Copilot); not possible in Codex
Both answers are recorded in metadata (cyrus-platforms, cyrus-invocation).

Creates <parent-dir>/<name>/ with:
  SKILL.md           from assets/skill-template.md
  evals/evals.json   from assets/evals-template.json
  agents/openai.yaml from assets/openai-yaml-template.yaml (explicit + codex, or --openai-yaml)
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

PLATFORMS = ("claude-code", "copilot", "codex", "claude-api")
DEFAULT_PLATFORMS = "claude-code,copilot,codex"
INVOCATIONS = ("implicit", "explicit", "background")
# Platforms that read the frontmatter invocation fields.
FRONTMATTER_INVOCATION_PLATFORMS = {"claude-code", "copilot"}

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


def parse_platforms(raw):
    platforms = [p.strip() for p in raw.split(",") if p.strip()]
    unknown = [p for p in platforms if p not in PLATFORMS]
    if unknown or not platforms:
        sys.exit(f"error: unknown or empty platform list {unknown or raw!r}; choose from {list(PLATFORMS)}")
    return [p for p in PLATFORMS if p in platforms]  # stable, de-duplicated order


def plan_invocation(invocation, platforms):
    """Return (frontmatter lines, need_openai_yaml, notes) or exit on impossible combos."""
    targets = set(platforms)
    if invocation != "implicit" and "claude-api" in targets:
        sys.exit(f"error: '{invocation}' invocation is not possible on claude.ai / Claude API uploads "
                 "(they reject the needed fields). Drop claude-api or use --invocation implicit.")
    fields, notes = [], []
    uses_frontmatter = bool(targets & FRONTMATTER_INVOCATION_PLATFORMS)
    if invocation == "explicit" and uses_frontmatter:
        fields.append("disable-model-invocation: true")
    if invocation == "background":
        if uses_frontmatter:
            fields.append("user-invocable: false")
        if "codex" in targets:
            notes.append("Codex has no hidden mode: the skill stays visible in /skills and $ mentions there.")
    need_openai_yaml = invocation == "explicit" and "codex" in targets
    return fields, need_openai_yaml, notes


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
    parser.add_argument("--platforms", default=DEFAULT_PLATFORMS,
                        help=f"comma-separated from {','.join(PLATFORMS)} (default: {DEFAULT_PLATFORMS})")
    parser.add_argument("--resources", default="", help="comma-separated: scripts,references,assets")
    parser.add_argument("--openai-yaml", action="store_true", help="always create agents/openai.yaml for Codex")
    args = parser.parse_args()

    name = normalise_name(args.name)
    problem = check_name(name)
    if problem:
        sys.exit(f"error: '{name}': {problem}")

    platforms = parse_platforms(args.platforms)
    fields, need_openai_yaml, notes = plan_invocation(args.invocation, platforms)
    if args.openai_yaml and "codex" not in platforms:
        notes.append("agents/openai.yaml is only read by Codex, which is not a target platform.")

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
