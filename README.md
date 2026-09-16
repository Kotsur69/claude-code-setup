# claude-code-setup

Portable Claude Code configuration — the ECC harness, hooks, rules and
conventions used on the main workstation, packaged so a second machine can be
brought to the same state.

Everything here installs into `~/.claude/`.

## What this gives you

| Layer | What it is | You interact with it |
|-------|------------|----------------------|
| Commands | `/ecc:*` slash commands (94) | Yes — you type these |
| Agents | `ecc:*` subagents (68) | No — they get dispatched for you |
| Skills | Auto-routing skill packs (286) | No — they fire on keywords |
| Rules | `rules/ecc/**` markdown, always loaded | No — invisible context |

The habit loop the whole thing is built around:

```
/ecc:plan           before any non-trivial change
   ...work...
/ecc:code-review    after writing code
/ecc:security-scan  before a commit
/ecc:build-fix      when the build or tests go red
```

Two commands replace the loop when you want to hand over a whole task:

```
/ecc:orch-add-feature   research -> plan -> TDD -> review -> gated commit
/ecc:orch-fix-defect    reproduce as a failing test first, then fix
```

For anything smaller than that — a single file, a typo, a config tweak — run
nothing. An agent starts with no conversation history, so the handoff cost only
pays off for bounded work.

## Install

### 1. Claude Code itself

Install Claude Code, sign in, then confirm the CLI works:

```powershell
claude --version
```

### 2. Drop in the config

```powershell
.\install.ps1
```

The script copies `CLAUDE.md`, `settings.json`, `settings.local.json`, the
hooks, the rules and the templates into `~/.claude/`, rewriting the hardcoded
`C:\Users\mmazur` paths in `settings.json` to the current user profile. It backs
up anything it is about to overwrite to `*.bak-<timestamp>`.

Run it with `-DryRun` first to see what it would touch.

### 3. Let the plugins install themselves

`settings.json` carries `extraKnownMarketplaces` and `enabledPlugins`, so on the
next `claude` launch the marketplaces are fetched and the plugins install
without further input:

| Plugin | Source |
|--------|--------|
| `ecc` | `https://github.com/affaan-m/ECC.git` |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` |
| `impeccable` | `pbakaus/impeccable` |
| `document-skills` | `anthropics/skills` |
| `frontend-design` | official marketplace |
| `diagram-design` | `cathrynlavery/diagram-design` |
| `last30days` | `mvanhorn/last30days-skill` |

Verify with `/plugin` and `/ecc:ecc-guide`.

### 4. Optional: codebase-memory

Not bundled — it is a separate binary that lands in `~/.local/bin/`. It provides
a code knowledge graph over MCP: `search_graph`, `trace_path`,
`get_code_snippet`, `query_graph`, `get_architecture`.

Two things worth knowing before you install it:

- **It is not automatic.** Indexing is triggered, not ambient. A repository has
  to be indexed with `index_repository` before any graph query returns anything
  for it. Leaving auto-index on is what produced a 318 MB cache full of junk
  indexes on the main machine — including one that indexed the `.claude` config
  directory itself at 121,161 nodes.
- **Port 9749 is a local web dashboard**, set by `ui_enabled` / `ui_port` in
  `~/.cache/codebase-memory-mcp/config.json`. It is not how Claude talks to the
  server — that happens over MCP stdio. Opening `http://localhost:9749` shows
  you the graph; closing it changes nothing about how Claude works. Set
  `ui_enabled: false` if you do not want the listener.

### 5. Files not in this repo

Deliberately excluded, because they are machine-local or contain credentials:

- `.credentials.json`, `.claude.json` — auth tokens and per-project history
- `projects/`, `sessions/`, `session-data/`, `history.jsonl` — session state
- `plugins/` — regenerated on first launch from `settings.json`
- `logs`, `telemetry/`, `metrics/`, `cache/` — machine-local noise
- `helpers/` — the statusline script and HTML cheatsheets; copy these by hand if
  you want them, and drop the `statusLine` block from `settings.json` if you do
  not

## Layout

```
CLAUDE.md                        global instructions (preferences, auto-routing)
settings.json                    hooks, plugins, marketplaces, statusline
settings.local.json              permission allowlist
mcp.json.example                 MCP servers, credentials as ${ENV_VAR}
rules/ecc/common/agents.md       patched agent-orchestration rule (see below)
hooks/cbm-session-reminder       SessionStart code-discovery reminder
hooks/cbm-subagent-reminder      same reminder for subagents
templates/repo-CLAUDE.md         per-repository template
install.ps1                      installer
```

## The patched rule

`rules/ecc/common/agents.md` here is **not** the version ECC ships. Upstream
states that agents live in `~/.claude/agents/` under bare names (`planner`,
`code-reviewer`). Neither is true for a plugin install: the agents live inside
the `ecc@ecc` plugin and resolve as `ecc:planner`, `ecc:code-reviewer`.

The failure is silent. The bare name does not resolve, no error surfaces, and
the work quietly gets done inline instead — so you stop getting agent
delegation without ever seeing it break. Reported upstream as
[affaan-m/ECC#3143](https://github.com/affaan-m/ECC/issues/3143).

**This matters for reinstalls.** ECC's installer calls `rules/ecc` a *managed*
directory and the `ecc` marketplace has `autoUpdate: true`, so an update can
overwrite the patch. That is why the same fact is also stated in `CLAUDE.md`,
which lives outside the managed tree and always wins.

## Per-repository setup

Copy `templates/repo-CLAUDE.md` into a repository root as `CLAUDE.md` and fill
in the stack-specific rows. The important part is the authorization block: by
default Claude Code will not use the Agent tool proactively unless the user, a
CLAUDE.md, or a skill asks it to. That file is how you grant it once instead of
asking every session.

A parent-directory `CLAUDE.md` applies to every repository beneath it, so the
general authorization can live one level up and only the stack-specific
triggers need to be per-repo.

## GateGuard

ECC ships a fact-forcing PreToolUse gate. The first Edit, Write or destructive
Bash call in a session is denied, with a demand for concrete facts — which files
import this one, which public API is affected, what the data schema looks like,
and the user instruction quoted verbatim. Presenting them allows the retry.

It is deny → force → allow, not a confirmation prompt, and the investigation is
the point: asking a model "are you sure?" does nothing, but making it grep for
importers changes what it writes. ECC measures +2.25/10 on output quality
against ungated runs.

Knobs, all environment variables:

| Variable | Effect |
|----------|--------|
| `ECC_GATEGUARD=off` | disables the gate entirely |
| `GATEGUARD_DISABLED` | same, alternate spelling |
| `GATEGUARD_EXEMPT_GLOBS` | path-scoped exemptions, e.g. `**/scratch/**` |
| `GATEGUARD_BASH_ROUTINE_DISABLED` | stop gating routine Bash, keep it for edits |
| `GATEGUARD_BASH_EXTRA_DESTRUCTIVE` | add your own destructive patterns |
| `GATEGUARD_FACT_FORCE_FULL_DENIALS` | verbose denial output |

Set them in the `env` block of `settings.json`.
