# CLAUDE.md

Instructions for Claude Code when working in this repository.

> Template. Copy to a repository root as `CLAUDE.md`, then replace the
> `<angle-bracket>` placeholders and delete the trigger rows that do not apply
> to this stack. The authorization block below is the part that matters — keep
> it as-is.

## Agent Delegation - Authorized

**This CLAUDE.md explicitly authorizes proactive use of the Agent tool in this
repository.** Claude Code's default guidance is "do not use the Agent tool
unless the user, *a CLAUDE.md file*, or a skill asks for it" - this file is that
authorization. Do not wait to be asked again.

ECC agents are plugin-scoped: invoke them as `Agent(subagent_type: "ecc:planner")`,
always with the `ecc:` prefix, never a bare name.

Delegate without prompting when:

| Trigger | Agent |
|---------|-------|
| Feature spanning 3+ modules | `ecc:planner` |
| Structural / architectural decision | `ecc:architect` |
| Bug fix or new feature needing tests | `ecc:tdd-guide` |
| Code just written or modified | `<stack reviewer, e.g. ecc:typescript-reviewer>` |
| `<security-sensitive surface for this repo>` | `ecc:security-reviewer` |
| `<build tool>` fails | `<ecc:*-build-resolver>` |
| Swallowed errors, silent fallbacks | `ecc:silent-failure-hunter` |
| Slow paths, memory growth | `ecc:performance-optimizer` |
| Dead code after a refactor | `ecc:refactor-cleaner` |

Pick the reviewer from the stack table in `rules/ecc/common/agents.md`, or run
`/ecc:ecc-guide` for the full roster.

**Do NOT delegate** trivial edits, single-file changes, or anything already
sized for one context. Agents start cold with no conversation history - the
handoff cost only pays off for bounded, self-contained work.

### Completion contract

Applies at every depth. **Your final message IS the deliverable.** Never end a
turn with "waiting for background agents" - ending your turn while children run
orphans their results. If you delegate, you own collection: wait, integrate,
then answer.

## Model Choice

The harness is model-independent. Hooks, rules, skills, ECC agents, and MCP
servers load identically on Opus and Sonnet - `/model` swaps the reasoning
engine, not the tooling.

| Use | Model |
|-----|-------|
| Architecture, hard debugging, large refactors, planning | Opus |
| Everyday edits, fast iterations, cheap loops | Sonnet |

## ECC Workflow In This Repo

Project context: `<framework and version, language, test runner, entry point,
and the npm/poetry scripts that actually exist>`

| Situation | Command |
|-----------|---------|
| Starting a non-trivial change | `/ecc:plan` - stops and waits for your confirm |
| Finished writing code | `/ecc:code-review` |
| Before a commit | `/ecc:security-scan` |
| Build or tests failing | `/ecc:build-fix` |
| Coverage gaps | `/ecc:test-coverage` |
| Full feature, end to end | `/ecc:orch-add-feature` |
| Bug, reproduced as a failing test first | `/ecc:orch-fix-defect` |
| Full roster of agents and skills | `/ecc:ecc-guide` |

### Repo-specific review focus

Write 3-5 bullets here. These are worth more than everything above, because
they are the only part a general-purpose agent cannot infer. Good ones name a
specific file or boundary and say what breaks:

- **`<the security boundary>`** - why it is one, and which agent should review it.
- **`<the data contract>`** - what the schema actually is, and how a change
  fails silently rather than loudly.
- **`<the thing that is not source>`** - data directories, caches, generated
  output that must not be edited by hand.
- **`<how a change is verified here>`** - the real command, or an honest note
  that there is no test suite and verification is manual.
