"""Rules shared by init_skill.py and validate_skill.py, so both scripts enforce the same ones.

A helper module that the scripts import. It's never run on its own, so it prints no trace line.
Standard library only.
"""
import re

# --- Agent Skills spec limits (the strictest values across the tools) ----------
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED_WORDS = ("claude", "anthropic")  # rejected by claude.ai uploads and the Claude API

# --- cyrus conventions ----------------------------------------------------------
PREFIX = "cyrus-"

# --- Platforms and invocation modes -------------------------------------------
PLATFORMS = ("claude-code", "copilot", "codex", "claude-api")
DEFAULT_PLATFORMS = ("claude-code", "copilot", "codex")
PLATFORM_LABELS = {"claude-code": "Claude Code", "copilot": "Copilot", "codex": "Codex", "claude-api": "claude.ai/API"}
INVOCATIONS = ("implicit", "explicit", "background")
# Platforms that read the frontmatter invocation fields (disable-model-invocation, user-invocable).
FRONTMATTER_INVOCATION_PLATFORMS = frozenset({"claude-code", "copilot"})


def labels(platforms):
    return ", ".join(PLATFORM_LABELS[p] for p in PLATFORMS if p in platforms)


def name_problems(name):
    """Return the ways a skill name breaks the spec, as a list of messages."""
    problems = []
    if not NAME_RE.match(name):
        problems.append(f"name '{name}': use lowercase a-z, 0-9 and single hyphens, with no leading or "
                        "trailing hyphen (Copilot silently skips skills with invalid names)")
    if len(name) > MAX_NAME_LEN:
        problems.append(f"name is {len(name)} chars; the limit is {MAX_NAME_LEN}")
    for word in RESERVED_WORDS:
        if word in name:
            problems.append(f"name contains the reserved word '{word}' (rejected by claude.ai and the Claude API)")
    return problems


def description_problems(text):
    """Return the ways a description breaks the spec, as a list of messages."""
    problems = []
    if len(text) > MAX_DESCRIPTION_LEN:
        problems.append(f"description is {len(text)} chars; the limit is {MAX_DESCRIPTION_LEN}")
    if "<" in text or ">" in text:
        problems.append("description must not contain angle brackets "
                        "(claude.ai rejects XML tags, and Claude Code escapes them)")
    return problems


class InvocationPlan:
    """The settings each target platform needs for one invocation mode.

    disable_model_invocation / user_invocable_false: frontmatter values that Claude Code and Copilot need.
    codex_implicit_off: whether agents/openai.yaml must set policy.allow_implicit_invocation: false.
    error: set when the mode is impossible on one of the targets.
    notes: limits the user should hear about.
    """

    def __init__(self, invocation, targets):
        targets = set(targets)
        self.invocation = invocation
        self.frontmatter_targets = targets & FRONTMATTER_INVOCATION_PLATFORMS
        self.disable_model_invocation = invocation == "explicit"
        self.user_invocable_false = invocation == "background"
        self.codex_implicit_off = invocation == "explicit" and "codex" in targets
        self.error = None
        self.notes = []
        if invocation != "implicit" and "claude-api" in targets:
            self.error = (f"'{invocation}' invocation is not possible on claude.ai/API uploads, which reject the "
                          "needed fields; drop claude-api from the platforms or use implicit")
        if invocation == "background" and "codex" in targets:
            self.notes.append("Codex has no hidden mode: the skill stays visible in /skills and $ mentions there")

    def frontmatter_fields(self):
        """The YAML lines to add to SKILL.md frontmatter for this plan."""
        if not self.frontmatter_targets:
            return []
        fields = []
        if self.disable_model_invocation:
            fields.append("disable-model-invocation: true")
        if self.user_invocable_false:
            fields.append("user-invocable: false")
        return fields
