# Evaluating a skill

Improve a skill based on what you observe it doing, not on guesses. No one test runner works across all three tools, so use the fixed eval file below with headless runs, and fall back to manual runs where you can't run headless.

## Contents

- [Who runs the tests](#who-runs-the-tests)
- [Eval file](#eval-file)
- [Loop](#loop)
- [Trigger tests](#trigger-tests)
- [Scenario tests](#scenario-tests)
- [Running in each tool](#running-in-each-tool)
- [Reading the results](#reading-the-results)

## Who runs the tests

| Who | What |
| --- | --- |
| **The agent** that wrote the skill (you) | Fills in the eval file, runs every trigger test and safe scenario headless on each target platform whose CLI is installed and signed in, grades the results and revises the skill |
| **The user** | Approves the headless runs once (they use the user's accounts and cost tokens), reviews the report, and runs the manual checklist you give them |

Leave these to the user as manual steps, and never run them yourself:

- platforms whose CLI isn't installed or signed in
- scenarios with real side effects (deploying, sending, deleting, publishing)
- anything that needs an interactive UI, such as VS Code or the Copilot cloud agent

## Eval file

`evals/evals.json` sits inside the skill folder. Nothing links to it, so agents never load it as context.

```json
{
  "skill": "cyrus-example",
  "trigger_tests": {
    "should_trigger": ["3+ realistic prompts phrased the way users talk"],
    "should_not_trigger": ["1-2 near misses that share keywords but need something else"]
  },
  "scenarios": [
    {
      "id": "basic",
      "prompt": "A realistic end-to-end request",
      "files": ["optional/input/files"],
      "expected_behavior": ["Observable outcome the run must show"]
    }
  ]
}
```

Write `expected_behavior` items as things you can check: files created, commands run, format followed, a step not skipped.

## Loop

1. **Baseline.** Run each scenario *without* the skill and note where the agent fails or wanders. These failures are what the skill must fix. If there are none, the skill may not be needed.
2. **Minimal skill.** Write just enough instruction to fix the observed failures.
3. **Run with the skill.** Use a fresh session each time, so earlier conversation doesn't leak into the result.
4. **Compare and revise.** Change the description for trigger problems, and the body for behaviour problems.
5. **Repeat** until every scenario meets its expected behaviour. Re-run the validator after each edit.

Useful split: one agent session writes the skill, and a separate fresh session uses it on real tasks. Watch how the user of the skill navigates it. If it skips a reference, reads files in an unexpected order, or relies too much on one file, that part of the structure is unclear.

## Trigger tests

In a fresh session, for each prompt:

- **`should_trigger`:** the skill should load without being named. For explicit skills (`cyrus-invocation: explicit`), reverse this: confirm the skill does **not** auto-load on these prompts.
- **`should_not_trigger`:** the skill should not load.

**How to tell whether it triggered:** search the captured output for the skill's trace line, `[skill] <name>`. If the tool's own log shows the skill loading but the trace line is missing, count it as triggered. Then fix the trace block, since the skill should always announce itself.

Fixes:

- **Triggers too rarely:** add the user's actual words to the description and put the key trigger words first.
- **Triggers too often:** narrow the scope and name what it is not for.
- **Over budget:** if many skills are installed, the tool may shorten the description. Check that its first sentence still makes the case on its own.

## Scenario tests

Invoke the skill explicitly (`/<name>` or `$<name>`) on each target platform recorded in `metadata.cyrus-platforms`, with each scenario prompt, then check each `expected_behavior` item. Also check:

- Did the agent read only the references it needed?
- Did it run scripts instead of rewriting them?
- Did it follow the verification loop?

## Running in each tool

At minimum, test in the tool the user uses most. Also test in the others when the skill relies on scripts, tool permissions or anything that behaves differently between tools.

| Tool | Interactive (user) | Headless (agent) |
| --- | --- | --- |
| Claude Code | `claude`, then `/<name> ...` | `claude -p --output-format stream-json --verbose "<prompt>"` (records every message, not just the final one) |
| Codex | `codex`, then `$<name> ...` | `codex exec --json "<prompt>"` |
| Copilot CLI | `copilot`, then `/<name> ...` (run `/skills reload` after adding the skill) | `copilot -p "<prompt>"` |

Headless flags change between versions, so check `--help` for each tool first. Capture both stdout and stderr (`2>&1`) so the trace lines are recorded.

**Isolated setup:** run each headless session in a throwaway directory with the skill installed at project level. That way the user's personal skill folders stay untouched, and no earlier context leaks into the run:

```bash
T="$(mktemp -d)" && cd "$T" && git init -q
mkdir -p .claude/skills .agents/skills
ln -s "<absolute-skill-dir>" ".claude/skills/<name>"   # Claude Code (Copilot also reads this)
ln -s "<absolute-skill-dir>" ".agents/skills/<name>"   # Codex + Copilot
```

Keep the default permission settings. Never pass flags that skip approvals or the sandbox, so a run can't make changes outside what's allowed. Put any input files a scenario needs into the directory first.

If the skill will be used with smaller or faster models, test with one of those too. They need more explicit guidance, while large models need less explanation.

## Reading the results

Report to the user:

- the trigger hit rate (for example, 3/3 should-trigger and 0/2 should-not)
- which scenarios passed or failed, and why
- what you changed in response
- for each platform, who tested it: you (headless), the user (manual), or nobody yet
- the manual checklist for the user, if anything is left

Don't claim cross-tool compatibility for a tool nobody tested.
