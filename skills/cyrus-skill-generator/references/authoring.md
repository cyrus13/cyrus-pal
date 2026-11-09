# Authoring best practices

How to write a skill's content. This combines the Agent Skills spec, Anthropic's skill-authoring guide, and the GitHub Copilot and OpenAI Codex docs.

## Contents

- [Principles](#principles)
- [Writing the description](#writing-the-description)
- [Structuring the body](#structuring-the-body)
- [Degrees of freedom](#degrees-of-freedom)
- [Progressive disclosure patterns](#progressive-disclosure-patterns)
- [Scripts](#scripts)
- [Trace logging](#trace-logging)
- [Assets](#assets)
- [Anti-patterns](#anti-patterns)

## Principles

- **Context is shared and limited.** Every token in SKILL.md competes with the user's code and conversation. Assume the agent is already capable, and for each paragraph ask: "Would the agent get this wrong without it?"
- **One skill, one job.** If a skill needs "and" to describe it, consider splitting it.
- **Write instructions, not documentation.** Use imperative steps with explicit inputs and outputs. Write for the agent, not for a human reader.
- **Start from real failures.** The best content corrects what the agent actually got wrong without the skill. See [evaluation.md](evaluation.md).
- **Keep the most important content first.** Tools truncate descriptions, and they keep only the start of the body after compaction.

## Writing the description

Tools pick a skill using its description alone, so it matters more than any other text in the skill.

- **Say what it does, then when to use it:** "Generates X from Y. Use when the user asks to ... or mentions ...".
- **Third person.** Write "Processes Excel files...", not "I can help..." or "You can use this to...".
- **Front-load the trigger words.** Include the nouns and verbs users actually type: file types, tool names, task names.
- **Be specific about scope.** Mention a near miss it should not cover if confusion is likely ("Not for X; use Y").
- **Limits:** 1024 characters, no angle brackets, one paragraph.
- **Don't repeat "when to use" in the body.** The body loads only after the skill triggers, so the agent has already decided by then.

Good:
> Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.

Bad: "Helps with PDFs." (too vague to trigger reliably)

## Structuring the body

A typical skeleton (the template in `assets/skill-template.md` follows it):

1. **Purpose:** one or two sentences on what it produces.
2. **Path note:** "Paths are relative to the directory containing this SKILL.md."
3. **Workflow:** numbered steps. For workflows longer than about 5 steps, give the agent a checklist to copy into its reply (`- [ ] Step 1 ...`) so progress is visible and steps aren't skipped.
4. **Verification loop:** "Run the validator, fix the errors, repeat; only continue when it passes." Make it explicit: "If verification fails, return to step N."
5. **Output format:** a template or example when the shape matters. Concrete input and output examples beat descriptions.
6. **Gotchas:** non-obvious pitfalls only.
7. **Resources:** each linked file, with "read when..." or "run to...".

Other rules:

- **Give a default, not a menu.** Write "Use pdfplumber. For scanned PDFs needing OCR, use pdf2image with pytesseract instead", not a list of five libraries.
- **Use consistent terms.** Pick one word for each concept ("endpoint", not a mix of endpoint, route and URL).
- **Avoid time-sensitive wording.** Don't write "until August, use the old API". If you need history, put it in a collapsed "Old patterns" section.
- **Name what must be installed.** List required packages and CLIs, and never assume they're present.
- **MCP tools:** use fully qualified names (`ServerName:tool_name`).

## Degrees of freedom

Match how specific an instruction is to how fragile the task is:

| Freedom | Form | Use when |
| --- | --- | --- |
| High | Prose guidance | Several approaches are valid and judgment matters (reviews, writing) |
| Medium | Pseudocode, a parameterized script, a template | There's a preferred pattern, with some variation allowed |
| Low | An exact command or script ("run exactly this; don't add flags") | Operations that are fragile, must happen in order, or are destructive (migrations, releases) |

Think of a narrow bridge with cliffs on both sides versus an open field: the narrow bridge needs exact steps, the open field only needs a direction.

## Progressive disclosure patterns

Keep SKILL.md under 500 lines (aim for under 200), and use it as a table of contents. Three ways to split content out:

1. **Overview plus references:** SKILL.md has the quick start, with pointers like "For the full API, read `references/api.md`".
2. **By domain or variant:** one reference file per domain (`references/aws.md`, `references/gcp.md`). SKILL.md says which to read, so the agent loads only one.
3. **Conditional detail:** "For tracked changes, read references/redlining.md". The agent loads the extra detail only when the case comes up.

Rules:

- **One level deep.** SKILL.md links to reference files, and reference files don't send the agent to further reference files. Agents read chained references only partly, for example with `head`.
- **Add a "Contents" list at the top of any reference file longer than 100 lines.** Agents often preview a file before reading the rest.
- **Keep each reference file to one topic.** Smaller files cost less context when loaded.
- **Large lookup data:** keep it in `assets/` or `references/`, and tell the agent to search it (grep) rather than read all of it.

## Scripts

Add a script when the agent would otherwise rewrite the same code each time, when a step must be exact, or to validate output. Scripts cost no context until they run, and then only their output counts.

- **Say whether to run it or read it.** "Run `scripts/fill_form.py <in> <out>`" versus "See `scripts/fill_form.py` for the algorithm".
- **Solve, don't defer.** Handle errors in the script (missing file, bad input) with clear messages instead of crashing and leaving the agent to work out why.
- **Explain every constant.** Write `TIMEOUT_S = 30  # p99 API latency is about 10s`, not a bare 47.
- **Make error messages say what to do next.** "Field 'sig_date' not found. Available: name, date, signature".
- **Plan, validate, execute** for bulk or destructive work: the agent writes a plan file, a script validates it, and only then does the agent apply it.
- **Portability.** Prefer Python 3 standard library or POSIX sh. Document any other dependencies in SKILL.md and in `compatibility`. Use forward-slash paths. Don't rely on tool-specific environment variables.
- **Make scripts self-locating.** Resolve sibling files relative to the script itself (in Python, `Path(__file__).parent`), not the current working directory.

## Trace logging

Every cyrus skill prints trace lines, so the console shows which skill ran and which copy of it. That matters when the same skill is installed in more than one place. Evals also use these lines to detect whether a skill triggered.

- **In SKILL.md:** the template puts a trace block right under the title. Keep it there. It has to be among the first lines so the agent reads it before anything else and it survives truncation. It asks the agent to print:
  - `[skill] <name> v<version> | started` before doing anything else
  - `[skill] <name> | finished` at the end, or `[skill] <name> | stopped: <reason>` if the workflow stops early
- **In scripts:** every script that gets run directly prints `[skill] <name> | scripts/<file>` to stderr as its first action. Using stderr keeps stdout clean for output that other tools parse.
  - Python: `print("[skill] cyrus-example | scripts/build.py", file=sys.stderr)`
  - Bash: `echo "[skill] cyrus-example | scripts/build.sh" >&2`
  - Helper modules that are only imported don't need a trace.
- **Keep the version current.** When you bump `metadata.version`, update the trace line too. The validator checks that they match.
- **Why an instruction and not a hook:** Claude Code can run hooks when a skill loads, but Copilot and Codex can't, so an instruction in the body is the only option that works everywhere. Models follow it reliably but not with certainty, while script traces always print. If a trace is missing, treat that as a bug in the skill and fix the body.

## Assets

Assets are files used in the output, not instructions: templates, boilerplate projects, fonts, images, schemas, sample data.

- Reference each asset from SKILL.md or from the script that uses it, so the agent knows it exists.
- Prefer one template with clear placeholders over prose describing a format.
- Keep binary assets small. They ship with every copy of the skill.

## Anti-patterns

- Backslash paths (`scripts\run.py`).
- Vague names or descriptions (`helper`, "does stuff with files").
- Writing the description in first or second person.
- Explaining things the agent already knows (what a PDF is, how git works).
- Deeply nested references, or resource files nothing links to.
- Too many options with no default.
- Tool-specific syntax in an otherwise portable skill.
- Unexplained constants and scripts that just crash.
- Assuming packages, CLIs or network access are available.
- Secrets or personal data inside the skill folder.
