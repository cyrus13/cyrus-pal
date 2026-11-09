#!/usr/bin/env python3
"""Validate an Agent Skill folder for spec compliance and cross-tool portability.

Usage:
  python3 validate_skill.py <skill-dir> [--strict] [--third-party]

Checks the Agent Skills spec (agentskills.io) plus the stricter rules of
Claude Code, GitHub Copilot, OpenAI Codex and claude.ai uploads:
frontmatter fields and limits, naming, description quality, body size,
tool-specific syntax, leftover placeholders, broken or missing resource
links, nested references, and the optional Codex agents/openai.yaml.

Checks are tailored to the skill's recorded choices in metadata:
  cyrus-platforms:  space-separated targets (claude-code copilot codex claude-api)
  cyrus-invocation: implicit | explicit | background
Without them, all of claude-code, copilot and codex are assumed.
--third-party skips the cyrus conventions (prefix, recorded choices, trace lines).

Prints ERROR / WARN lines. Exit code: 1 if any ERROR (or any WARN with
--strict), otherwise 0. Standard library only.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Limits from the Agent Skills spec (strictest values across the tools).
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MAX_COMPATIBILITY_LEN = 500
MAX_BODY_LINES = 500  # spec and Anthropic guidance: keep SKILL.md under 500 lines
MAX_BODY_TOKENS = 5000  # spec recommendation for the activated body
CHARS_PER_TOKEN = 4  # rough English average; good enough for a size warning
CLAUDE_LISTING_CAP = 1536  # Claude Code truncates description + when_to_use here
TOC_REQUIRED_LINES = 100  # Anthropic guidance: add a contents list past this length
MIN_DESCRIPTION_LEN = 40  # shorter descriptions are almost always too vague to trigger
TRACE_MAX_LINE = 15  # the trace instruction must come before the workflow, so the agent reads it first
TRACE = "[skill] cyrus-skill-generator | scripts/validate_skill.py"
SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".js", ".mjs", ".ts", ".ps1"}

PREFIX = "cyrus-"
RESERVED_WORDS = ("claude", "anthropic")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

PLATFORMS = ("claude-code", "copilot", "codex", "claude-api")
DEFAULT_TARGETS = {"claude-code", "copilot", "codex"}
INVOCATIONS = ("implicit", "explicit", "background")
FRONTMATTER_INVOCATION_PLATFORMS = {"claude-code", "copilot"}  # read disable-model-invocation / user-invocable

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Non-spec fields -> platforms that act on them. claude.ai uploads and the Claude API reject all of them.
CC_COPILOT = {"claude-code", "copilot"}
CC = {"claude-code"}
EXTENSION_SUPPORT = {
    "disable-model-invocation": CC_COPILOT,
    "user-invocable": CC_COPILOT,
    "argument-hint": CC_COPILOT,
    "context": CC_COPILOT,
    "when_to_use": CC,
    "paths": CC,
    "arguments": CC,
    "disallowed-tools": CC,
    "model": CC,
    "effort": CC,
    "agent": CC,
    "background": CC,
    "hooks": CC,
    "shell": CC,
}
EXTENSION_HINTS = {
    "when_to_use": "; fold it into description",
    "paths": "; name the file types in description instead",
    "argument-hint": "; describe the expected input in the body",
}
# Invocation fields are checked against cyrus-invocation instead of per-platform support.
INVOCATION_FIELDS = {"disable-model-invocation", "user-invocable"}
OPENAI_YAML_KEYS = {"interface", "policy", "dependencies"}
PLATFORM_LABELS = {"claude-code": "Claude Code", "copilot": "Copilot", "codex": "Codex", "claude-api": "claude.ai/API"}

RESOURCE_DIRS = ("scripts", "references", "assets")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".js", ".mjs", ".ts", ".json", ".yaml", ".yml", ".txt", ".toml"}
IGNORED_PARTS = {"__pycache__", "node_modules", ".git"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# Bare mentions like scripts/run.py. The lookbehind skips .agents/, ~/.agents/ and URL paths.
MENTION_RE = re.compile(r"(?<![\w./~-])((?:scripts|references|assets|agents)/[A-Za-z0-9_./-]*[A-Za-z0-9_])")
PLACEHOLDER_RE = re.compile(r"\bTODO\b|\{\{[^}]*\}\}")
CLAUDE_ONLY_RE = [
    (re.compile(r"\$ARGUMENTS\b|\$\{CLAUDE_[A-Z_]+\}"), "argument / ${CLAUDE_*} substitution"),
    (re.compile(r"(?:^|\s)!`[^`]+`"), "!`command` shell injection"),
    (re.compile(r"^\s*```!", re.M), "```! shell injection block"),
]
COPILOT_ONLY_RE = re.compile(r"#file:")
FIRST_SECOND_PERSON_RE = re.compile(r"^\s*(I|I'm|I am|We|You|Your)\b|\bI can help\b|\bYou can use\b", re.I)
TRIGGER_CUE_RE = re.compile(r"\b(use (it |this )?(when|for|to|whenever|if)|when (the )?user|whenever|trigger)", re.I)
YAML_SPECIAL_PLAIN = re.compile(r"^(true|false|yes|no|on|off|null|~|-?\d+(\.\d+)?)$", re.I)


class FrontmatterError(Exception):
    pass


class Scalar(str):
    """A parsed YAML scalar that remembers whether it was quoted."""

    def __new__(cls, value, quoted=False):
        obj = super().__new__(cls, value)
        obj.quoted = quoted
        return obj


class Complex:
    """A nested YAML value too complex for this parser (validated only loosely)."""

    def __init__(self, lines):
        self.lines = lines


# --- minimal YAML subset parser -------------------------------------------
# Supports what SKILL.md frontmatter needs: plain/quoted scalars, block
# scalars (| >), one-level lists and string maps, and flow lists [a, b].
# Anything else is reported, because Claude Code silently drops all fields
# when frontmatter YAML is malformed.

KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:[ \t]+(.*))?$")


def parse_scalar(raw, lineno):
    raw = raw.strip()
    if raw.startswith('"'):
        try:
            return Scalar(json.loads(raw), quoted=True)
        except ValueError:
            raise FrontmatterError(f"frontmatter line {lineno}: malformed double-quoted string")
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            raise FrontmatterError(f"frontmatter line {lineno}: unterminated single-quoted string")
        return Scalar(raw[1:-1].replace("''", "'"), quoted=True)
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    if raw.startswith("{"):
        raise FrontmatterError(f"frontmatter line {lineno}: flow mappings are not supported; use indented keys")
    if raw.startswith(("&", "*", "!", "%", "@", "`")):
        raise FrontmatterError(f"frontmatter line {lineno}: value starts with reserved YAML character; quote it")
    if ": " in raw or raw.endswith(":"):
        raise FrontmatterError(
            f"frontmatter line {lineno}: plain value contains ': ' which YAML reads as a mapping; quote the value"
        )
    return Scalar(raw)


def parse_block(lines, style):
    texts = [line.strip() for line in lines]
    while texts and not texts[-1]:
        texts.pop()
    if style.startswith("|"):
        return Scalar("\n".join(texts))
    paragraphs, current = [], []
    for text in texts:
        if text:
            current.append(text)
        else:
            paragraphs.append(" ".join(current))
            current = []
    paragraphs.append(" ".join(current))
    return Scalar("\n".join(p for p in paragraphs if p))


def parse_nested(lines, first_lineno):
    content = [(i, l) for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("#")]
    if not content:
        return Scalar("")
    indents = {len(l) - len(l.lstrip()) for _, l in content}
    if len(indents) > 1:
        return Complex(lines)
    if all(l.strip().startswith("- ") or l.strip() == "-" for _, l in content):
        items = []
        for i, l in content:
            item = l.strip()[1:].strip()
            if KEY_RE.match(item):
                return Complex(lines)
            items.append(parse_scalar(item, first_lineno + i))
        return items
    mapping = {}
    for i, l in content:
        m = KEY_RE.match(l.strip())
        if not m:
            return Complex(lines)
        if m.group(2) is None:
            return Complex(lines)
        mapping[m.group(1)] = parse_scalar(m.group(2), first_lineno + i)
    return mapping


def parse_frontmatter(lines, offset=2):
    data, order = {}, []
    i = 0
    while i < len(lines):
        line = lines[i]
        lineno = offset + i
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            raise FrontmatterError(f"frontmatter line {lineno}: unexpected indentation")
        m = KEY_RE.match(line.rstrip())
        if not m:
            raise FrontmatterError(f"frontmatter line {lineno}: expected 'key: value', got {line.strip()!r}")
        key, raw = m.group(1), (m.group(2) or "").strip()
        if key in data:
            raise FrontmatterError(f"frontmatter line {lineno}: duplicate key '{key}'")
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j][0] in " \t"):
            j += 1
        child = lines[i + 1 : j]
        if re.match(r"^[|>][+-]?$", raw):
            value = parse_block(child, raw)
        elif raw == "":
            value = parse_nested(child, lineno + 1)
        elif raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            value = [parse_scalar(x, lineno) for x in inner.split(",")] if inner else []
        else:
            if any(l.strip() for l in child):
                raise FrontmatterError(f"frontmatter line {lineno + 1}: unexpected indented line after '{key}'")
            value = parse_scalar(raw, lineno)
        data[key] = value
        order.append(key)
        i = j
    return data


# --- checks ------------------------------------------------------------------


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def as_text(value):
    if isinstance(value, str):
        return str(value)
    return None


def flag(value):
    """Return True/False for YAML-style booleans, None if absent or not boolean."""
    text = (as_text(value) or "").strip().lower()
    if text in ("true", "yes", "on", "1"):
        return True
    if text in ("false", "no", "off", "0"):
        return False
    return None


def labels(platforms):
    return ", ".join(PLATFORM_LABELS[p] for p in PLATFORMS if p in platforms)


def read_choices(fm, report, conventions):
    """Return (targets, invocation) from metadata.cyrus-platforms / cyrus-invocation."""
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    targets = set(DEFAULT_TARGETS)
    raw = meta.get("cyrus-platforms")
    if raw is None:
        if conventions:
            report.warn("metadata.cyrus-platforms is missing; record the target platforms, e.g. "
                        "cyrus-platforms: \"claude-code copilot codex\" (assuming those three)")
    else:
        given = set(raw.split())
        unknown = given - set(PLATFORMS)
        if unknown or not given:
            report.error(f"metadata.cyrus-platforms has unknown or no values {sorted(unknown)}; "
                         f"use a space-separated subset of: {' '.join(PLATFORMS)}")
        if given & set(PLATFORMS):
            targets = given & set(PLATFORMS)

    invocation = meta.get("cyrus-invocation")
    if invocation is None:
        if conventions:
            report.warn("metadata.cyrus-invocation is missing; record implicit, explicit or background")
    elif invocation not in INVOCATIONS:
        report.error(f"metadata.cyrus-invocation '{invocation}' must be one of: {', '.join(INVOCATIONS)}")
        invocation = None
    return targets, invocation


def check_name(fm, skill_dir, report, prefix_check):
    name = as_text(fm.get("name"))
    dir_name = os.path.basename(os.path.abspath(skill_dir))
    if not name:
        report.error("'name' is required by the spec, Copilot and Codex")
        return None
    if not NAME_RE.match(name):
        report.error(f"name '{name}': use lowercase a-z, 0-9 and single hyphens, no leading/trailing hyphen "
                     "(Copilot silently skips invalid names)")
    if len(name) > MAX_NAME_LEN:
        report.error(f"name is {len(name)} chars; limit is {MAX_NAME_LEN}")
    if name != dir_name:
        report.error(f"name '{name}' must match its folder name '{dir_name}'")
    for word in RESERVED_WORDS:
        if word in name:
            report.error(f"name contains reserved word '{word}' (rejected by claude.ai and the Claude API)")
    if prefix_check and not name.startswith(PREFIX):
        report.warn(f"name should start with '{PREFIX}' (cyrus-pal convention); pass --third-party for third-party skills")
    return name


def check_description(fm, report, invocation):
    desc = fm.get("description")
    text = as_text(desc)
    if desc is None or not (text or "").strip():
        report.error("'description' is required; tools pick skills from it alone")
        return
    if text is None:
        report.error("'description' must be a single string")
        return
    if len(text) > MAX_DESCRIPTION_LEN:
        report.error(f"description is {len(text)} chars; limit is {MAX_DESCRIPTION_LEN}")
    if "<" in text or ">" in text:
        report.error("description must not contain angle brackets (claude.ai rejects XML tags; Claude Code escapes them)")
    if len(text) < MIN_DESCRIPTION_LEN:
        report.warn(f"description is only {len(text)} chars; say what the skill does and when to use it")
    if FIRST_SECOND_PERSON_RE.search(text):
        report.warn("description should be third person ('Generates X...'), not 'I'/'You'/'We'")
    if invocation != "explicit" and not TRIGGER_CUE_RE.search(text):
        report.warn("description should say when to use the skill, e.g. 'Use when the user asks to ...'")
    extra = as_text(fm.get("when_to_use")) or ""
    if len(text) + len(extra) > CLAUDE_LISTING_CAP:
        report.warn(f"description + when_to_use exceed {CLAUDE_LISTING_CAP} chars; Claude Code truncates the listing")


def check_optional_fields(fm, report, targets):
    compat = fm.get("compatibility")
    if compat is not None:
        text = as_text(compat)
        if not text:
            report.error("'compatibility' must be a non-empty string (or be omitted)")
        elif len(text) > MAX_COMPATIBILITY_LEN:
            report.error(f"compatibility is {len(text)} chars; limit is {MAX_COMPATIBILITY_LEN}")

    meta = fm.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            report.error("'metadata' must be a map of string keys to string values")
        else:
            for key, value in meta.items():
                if not value.quoted and YAML_SPECIAL_PLAIN.match(value):
                    report.warn(f"metadata.{key}: quote '{value}' so YAML reads it as a string (spec requires strings)")

    tools = fm.get("allowed-tools")
    if tools is not None and not isinstance(tools, str):
        report.warn("'allowed-tools': the spec expects a space-separated string; lists work only in Claude Code")

    license_ = fm.get("license")
    if license_ is not None and not as_text(license_):
        report.error("'license' must be a short string, e.g. 'MIT' or 'LICENSE.txt has full terms'")

    for key, value in fm.items():
        if isinstance(value, Complex) and key not in ("hooks",):
            report.warn(f"'{key}' uses nested YAML this validator does not check; keep frontmatter simple")
        if key in SPEC_FIELDS:
            continue
        if "claude-api" in targets:
            report.error(f"'{key}' is not an Agent Skills spec field; claude.ai uploads and the Claude API "
                         "reject it (claude-api is a target platform)")
            continue
        if key in INVOCATION_FIELDS:
            continue  # checked against cyrus-invocation in check_invocation
        if key in EXTENSION_SUPPORT:
            ignored_by = targets - EXTENSION_SUPPORT[key]
            if ignored_by:
                report.warn(f"'{key}' is ignored by {labels(ignored_by)} (supported only by "
                            f"{labels(EXTENSION_SUPPORT[key])}){EXTENSION_HINTS.get(key, '')}")
        else:
            report.warn(f"unknown field '{key}': not in the spec or any target's docs; tools ignore or reject it")


def check_body(body, report, targets):
    lines = body.splitlines()
    if not body.strip():
        report.error("SKILL.md body is empty; add the instructions")
        return
    if len(lines) > MAX_BODY_LINES:
        report.warn(f"body is {len(lines)} lines; keep SKILL.md under {MAX_BODY_LINES} and move detail to references/")
    tokens = len(body) // CHARS_PER_TOKEN
    if tokens > MAX_BODY_TOKENS:
        report.warn(f"body is ~{tokens} tokens; the spec recommends under {MAX_BODY_TOKENS}")
    non_claude = targets - {"claude-code"}
    for pattern, label in CLAUDE_ONLY_RE:
        if non_claude and pattern.search(body):
            report.warn(f"body uses Claude Code-only {label}; {labels(non_claude)} see it as literal text - "
                        "add a plain-language fallback or remove it")
    non_copilot = targets - {"copilot"}
    if non_copilot and COPILOT_ONLY_RE.search(body):
        report.warn(f"body uses Copilot-only '#file:' references, which {labels(non_copilot)} ignore; "
                    "use Markdown links instead")


def check_placeholders(text, where, report, level="error"):
    found = sorted(set(m.group(0) for m in PLACEHOLDER_RE.finditer(text)))
    if found:
        msg = f"{where} still has template placeholders: {', '.join(found[:5])}"
        report.error(msg) if level == "error" else report.warn(msg)


def iter_skill_files(skill_dir):
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir)
        if any(part in IGNORED_PARTS or part.startswith(".") for part in rel.parts):
            continue
        if path.is_file():
            yield path, rel


def collect_refs(text, base_dir, skill_dir):
    """Return (resolved links, resolved bare mentions, bad links) found in text."""
    links, mentions, bad = set(), set(), []
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        if "\\" in clean:
            bad.append((target, "uses backslashes; use forward slashes"))
            continue
        resolved = (base_dir / clean).resolve()
        try:
            resolved.relative_to(skill_dir.resolve())
        except ValueError:
            bad.append((target, "points outside the skill folder; skills must be self-contained"))
            continue
        if not resolved.exists():
            bad.append((target, "does not exist"))
            continue
        links.add(resolved)
    for mention in MENTION_RE.findall(text):
        resolved = (skill_dir / mention).resolve()
        if resolved.exists():
            mentions.add(resolved)
    return links, mentions, bad


def check_resources(skill_dir, body, report):
    skill_root = skill_dir.resolve()
    links, mentions, bad = collect_refs(body, skill_dir, skill_dir)
    for target, why in bad:
        report.error(f"SKILL.md link '{target}' {why}")
    bad_targets = {target.split("#", 1)[0].lstrip("./") for target, _ in bad}
    for mention in MENTION_RE.findall(body):
        if mention in bad_targets:
            continue  # already reported as a broken link
        if not (skill_dir / mention).exists():
            report.warn(f"SKILL.md mentions '{mention}', which does not exist")
    if re.search(r"(?:scripts|references|assets)\\\w", body):
        report.warn("SKILL.md contains a backslash path; use forward slashes for portability")

    from_skill_md = links | mentions
    referenced = set(from_skill_md)
    ref_docs = [p for p, rel in iter_skill_files(skill_dir) if rel.parts[0] == "references" and p.suffix == ".md"]

    for path, rel in iter_skill_files(skill_dir):
        if rel.parts[0] in ("evals", "agents") or rel.name == "SKILL.md":
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            l2, m2, _ = collect_refs(text, path.parent, skill_dir)
            referenced |= l2 | m2
            # Agent-facing script/asset names also count when mentioned by bare file name.
            for other, other_rel in iter_skill_files(skill_dir):
                if other_rel.name in text and other != path:
                    referenced.add(other.resolve())

    for doc in ref_docs:
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = doc.relative_to(skill_dir)
        doc_links, _, doc_bad = collect_refs(text, doc.parent, skill_dir)
        for target, why in doc_bad:
            report.warn(f"{rel}: link '{target}' {why}")
        for target in doc_links:
            if target.suffix == ".md" and target.parent.name == "references" and target not in from_skill_md:
                report.warn(f"{rel} links to {target.relative_to(skill_root)}, which SKILL.md does not link: "
                            "nested reference chain - link it from SKILL.md instead")
        lines = text.splitlines()
        if len(lines) > TOC_REQUIRED_LINES:
            head = "\n".join(lines[:40])
            if not re.search(r"^#+\s*(table of )?contents\b", head, re.I | re.M):
                report.warn(f"{rel} is {len(lines)} lines; add a '## Contents' list near the top")

    for path, rel in iter_skill_files(skill_dir):
        if rel.parts[0] not in RESOURCE_DIRS:
            continue
        if path.resolve() not in referenced:
            report.warn(f"{rel} is not referenced from SKILL.md (Copilot only loads referenced files; "
                        "link it or delete it)")


def read_openai_yaml(skill_dir, targets, report):
    """Lint agents/openai.yaml; return True if it disables implicit invocation."""
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        return False
    if "codex" not in targets:
        report.warn("agents/openai.yaml is only read by Codex, which is not a target platform; remove it "
                    "or add codex to metadata.cyrus-platforms")
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^([A-Za-z0-9_-]+):", line)
        if m and m.group(1) not in OPENAI_YAML_KEYS:
            report.warn(f"agents/openai.yaml line {lineno}: unknown top-level key '{m.group(1)}' "
                        f"(documented: {', '.join(sorted(OPENAI_YAML_KEYS))})")
    check_placeholders(text, "agents/openai.yaml", report)
    return bool(re.search(r"^\s+allow_implicit_invocation:\s*false\b", text, re.M))


def check_invocation(skill_dir, fm, invocation, targets, report):
    """Make each target platform's invocation settings agree with the chosen mode."""
    implicit_off = read_openai_yaml(skill_dir, targets, report)
    dmi_on = flag(fm.get("disable-model-invocation")) is True
    hidden = flag(fm.get("user-invocable")) is False
    fm_targets = targets & FRONTMATTER_INVOCATION_PLATFORMS
    codex = "codex" in targets
    yaml_fix = "set policy.allow_implicit_invocation: false in agents/openai.yaml"

    if invocation is None:  # choice not recorded: only check the platforms agree with each other
        if dmi_on and codex and not implicit_off:
            report.warn(f"disable-model-invocation is true but Codex will still auto-invoke; {yaml_fix}")
        if implicit_off and not dmi_on and fm_targets:
            report.warn(f"agents/openai.yaml disables implicit invocation but {labels(fm_targets)} will "
                        "still auto-load; add disable-model-invocation: true")
        return

    if invocation != "implicit" and "claude-api" in targets:
        report.error(f"'{invocation}' invocation is not possible on claude.ai/API uploads; "
                     "drop claude-api from cyrus-platforms or use implicit")
    if invocation == "explicit":
        if fm_targets and not dmi_on:
            report.error(f"explicit invocation needs disable-model-invocation: true for {labels(fm_targets)}")
        if codex and not implicit_off:
            report.error(f"explicit invocation needs Codex support: {yaml_fix}")
        if hidden:
            report.error("explicit skills must not set user-invocable: false (nobody could invoke them)")
    elif invocation == "background":
        if fm_targets and not hidden:
            report.error(f"background invocation needs user-invocable: false for {labels(fm_targets)}")
        if dmi_on or implicit_off:
            report.error("background skills must allow implicit invocation (otherwise nothing can load them)")
        if codex:
            report.warn("Codex has no hidden mode: this skill stays visible there")
    else:  # implicit
        if dmi_on:
            report.error("disable-model-invocation: true contradicts cyrus-invocation: implicit; "
                         "remove it or change cyrus-invocation to explicit")
        if hidden:
            report.error("user-invocable: false contradicts cyrus-invocation: implicit; "
                         "remove it or change cyrus-invocation to background")
        if implicit_off:
            report.error("agents/openai.yaml disables implicit invocation, contradicting cyrus-invocation: implicit")


def check_trace(skill_dir, fm, body, report):
    """cyrus convention: skills and their scripts print a trace line identifying themselves."""
    name = as_text(fm.get("name"))
    if not name:
        return
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    version = meta.get("version")
    expected = f"[skill] {name}{' v' + version if version else ''} | started"
    started = re.search(r"\[skill\] " + re.escape(name) + r"(?: v([^\s|`]+))? \| started", body)
    if not started:
        report.error(f"SKILL.md must tell the agent to print the trace line '{expected}' first "
                     "(copy the trace block from the skill template)")
    else:
        line = body[: started.start()].count("\n") + 1
        if line > TRACE_MAX_LINE:
            report.warn(f"trace instruction is on body line {line}; move it right under the title so it is read first")
        traced_version = started.group(1)
        if version and traced_version and traced_version != version:
            report.error(f"trace line says v{traced_version} but metadata.version is {version}; update the trace line")
        elif version and not traced_version:
            report.warn(f"trace line should include the version: '{expected}'")
    if not re.search(r"\[skill\] " + re.escape(name) + r" \| finished", body):
        report.warn(f"SKILL.md should also tell the agent to print '[skill] {name} | finished' when done")

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for path, rel in iter_skill_files(skill_dir):
            if rel.parts[0] != "scripts" or path.suffix.lower() not in SCRIPT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"[skill] {name}" not in text:
                report.warn(f"{rel} does not print its trace line '[skill] {name} | {rel.as_posix()}' to stderr "
                            "(fine for helper modules that are only imported)")


def check_evals(skill_dir, report, invocation):
    path = skill_dir / "evals" / "evals.json"
    if not path.exists():
        report.warn("no evals/evals.json; add trigger tests and scenarios (see references on evaluation)")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        report.error(f"evals/evals.json is not valid JSON: {exc}")
        return
    check_placeholders(json.dumps(data), "evals/evals.json", report, level="warn")
    triggers = data.get("trigger_tests", {}) if isinstance(data, dict) else {}
    if invocation != "explicit" and len(triggers.get("should_trigger", [])) < 3:
        report.warn("evals/evals.json: add at least 3 should_trigger prompts")


def validate(skill_dir, conventions=True):
    report = Report()
    skill_md = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        report.error(f"{skill_dir} is not a directory")
        return report
    if not skill_md.is_file():
        others = [p.name for p in skill_dir.iterdir() if p.name.lower() == "skill.md"]
        hint = f" (found {others[0]}; the file must be named exactly SKILL.md)" if others else ""
        report.error(f"missing SKILL.md{hint}")
        return report

    raw = skill_md.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        report.error("SKILL.md starts with a UTF-8 BOM; remove it so '---' is the very first line")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        report.error("SKILL.md is not valid UTF-8")
        return report
    if "\r\n" in text:
        report.warn("SKILL.md uses CRLF line endings; prefer LF")
        text = text.replace("\r\n", "\n")

    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        report.error("SKILL.md must start with '---' on the first line (YAML frontmatter)")
        return report
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        report.error("frontmatter is not closed with a '---' line")
        return report
    try:
        fm = parse_frontmatter(lines[1:end])
    except FrontmatterError as exc:
        report.error(f"{exc} (Claude Code drops ALL fields when frontmatter YAML is malformed)")
        return report
    body = "\n".join(lines[end + 1 :])

    targets, invocation = read_choices(fm, report, conventions)
    check_name(fm, skill_dir, report, conventions)
    check_description(fm, report, invocation)
    check_optional_fields(fm, report, targets)
    check_placeholders("\n".join(lines[: end + 1]), "frontmatter", report)
    check_placeholders(body, "SKILL.md body", report)
    check_body(body, report, targets)
    check_resources(skill_dir, body, report)
    check_invocation(skill_dir, fm, invocation, targets, report)
    check_evals(skill_dir, report, invocation)
    if conventions:
        check_trace(skill_dir, fm, body, report)
    report.targets, report.invocation = targets, invocation
    return report


def main():
    parser = argparse.ArgumentParser(description="Validate an Agent Skill folder.")
    parser.add_argument("skill_dir", help="path to the skill folder (the one containing SKILL.md)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--third-party", "--no-prefix-check", dest="third_party", action="store_true",
                        help="skip cyrus conventions (cyrus- prefix, recorded platforms/invocation, trace lines)")
    args = parser.parse_args()
    print(TRACE, file=sys.stderr)

    skill_dir = Path(args.skill_dir).expanduser()
    report = validate(skill_dir, conventions=not args.third_party)
    for msg in report.errors:
        print(f"ERROR  {msg}")
    for msg in report.warnings:
        print(f"WARN   {msg}")
    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    status = "FAIL" if failed else "PASS"
    scope = ""
    if hasattr(report, "targets"):
        scope = f" [targets: {labels(report.targets)}; invocation: {report.invocation or 'unrecorded'}]"
    print(f"{status}  {skill_dir}{scope}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
