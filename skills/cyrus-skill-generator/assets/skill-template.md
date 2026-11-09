---
name: {{name}}
description: {{description}}
{{invocation_fields}}license: MIT
metadata:
  author: cyrus13
  version: "0.1.0"
  cyrus-platforms: "{{platforms}}"
  cyrus-invocation: "{{invocation}}"
---

# {{title}}

**Trace (do this first):** before anything else, print this exact line on its own: `[skill] {{name}} v0.1.0 | started`. When the workflow ends, print `[skill] {{name}} | finished`. If you stop early, print `[skill] {{name}} | stopped: <reason>` instead.

TODO: One or two sentences on what this skill produces. Don't explain when to use it here. The description already covers that, and this body loads only after the skill triggers.

Paths in this skill are relative to the directory containing this SKILL.md.

## Workflow

1. TODO: First step, with its input and output.
2. TODO: Next step.
3. Verify: TODO: how to check the result (a command, a validator script or a checklist). If it fails, fix it and repeat from step 2.

## Output

TODO: The exact format of what the skill delivers, ideally a short example. Delete this section if the format is obvious.

## Gotchas

- TODO: Pitfalls the agent would get wrong without being told. Delete this section if there are none.

## Resources

- TODO: Link each file in references/, scripts/ and assets/, with a one-line "Read when..." or "Run to...". Delete this section if the skill has no resources.
