# Evaluating a skill

Improve a skill based on what you observe it doing, not on guesses. No one test runner works across all three tools, so use the fixed eval file below with manual or headless runs.

## Contents

- [Eval file](#eval-file)
- [Loop](#loop)
- [Trigger tests](#trigger-tests)
- [Scenario tests](#scenario-tests)
- [Running in each tool](#running-in-each-tool)
- [Reading the results](#reading-the-results)

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

- **`should_trigger`:** the skill should load without being named. Check that the tool shows the skill being used. For explicit skills (`cyrus-invocation: explicit`), reverse this: confirm the skill does **not** auto-load on these prompts.
- **`should_not_trigger`:** the skill should not load.

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

| Tool | Interactive | Headless (for scripted runs) |
| --- | --- | --- |
| Claude Code | `claude`, then `/<name> ...` | `claude -p "<prompt>"` |
| Codex | `codex`, then `$<name> ...` | `codex exec "<prompt>"` |
| Copilot CLI | `copilot`, then `/<name> ...` (run `/skills reload` after adding the skill) | `copilot -p "<prompt>"` |

Headless flags change between versions, so check `--help` for each tool. Install the skill where each tool will find it first (see [compatibility.md](compatibility.md)).

If the skill will be used with smaller or faster models, test with one of those too. They need more explicit guidance, while large models need less explanation.

## Reading the results

Report to the user:

- the trigger hit rate (for example, 3/3 should-trigger and 0/2 should-not)
- which scenarios passed or failed, and why
- what you changed in response

Don't claim cross-tool compatibility for a tool you didn't test. Say which tools you actually ran.
