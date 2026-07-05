# Setup on a new machine

This repo is a portable copy of the Claude Code environment from the original PC:
ruflo/claude-flow config, custom agents, the graphify skill, hooks, and all MCP
server configs (with real API keys — repo is private, that's the whole point).

## 1. Clone into place

```
git clone <this-repo-url> "%USERPROFILE%\.local\bin"
cd %USERPROFILE%\.local\bin
npm install
npm install -g ruflo   # or whatever package provides the `ruflo` / claude-flow CLI
```

## 2. Copy the global files into `~/.claude/`

These apply across *all* projects, not just this one:

```
copy global\CLAUDE.md            %USERPROFILE%\.claude\CLAUDE.md
copy global\settings.json        %USERPROFILE%\.claude\settings.json
copy global\settings.local.json  %USERPROFILE%\.claude\settings.local.json
copy global\credentials.json     %USERPROFILE%\.claude\.credentials.json
copy global\gmail_token.json     %USERPROFILE%\.claude\gmail_token.json
copy global\google_calendar_token.json %USERPROFILE%\.claude\google_calendar_token.json
```

The Gmail/Calendar tokens are OAuth refresh tokens — they should just work without
re-authenticating. If Google rejects them (revoked, expired, or scope mismatch),
run `python scripts\auth_google_calendar_mcp.py` once to redo the browser OAuth flow
(it uses the `client_secret_*.json` already sitting in `scripts/`).

## 3. MCP servers

`.mcp.json` in this repo root is a **project-scoped** MCP config — Claude Code
picks it up automatically when you open this folder, using `${CLAUDE_PROJECT_DIR}`
so paths resolve correctly regardless of your username on the new machine.

A few servers still hardcode the *original* PC's paths and won't work as-is:

- `filesystem` — the three allowed directories are `Kotsur69`-specific. Edit to match
  the new machine's folder layout (or just remove ones you don't need).
- `obsidian` — points at the personal Ideaverse vault. Skip if you don't have one here.
- `graphify-crypto` / `graphify-synthara` / `graphify-luna` — each points at a graph
  file inside a specific side-project repo. They'll only work if you also clone that
  project to the same absolute path. Otherwise just ignore/remove those three entries.
- `postgres` / `redis` — point at `localhost` dev databases from the original machine.
  Harmless if unused, won't connect unless you spin up the same local services.

Everything else (context7, playwright, firecrawl, cloudflare, resend, tavily, e2b,
replicate, axiom, browserbase, sentry, linear, stripe, slack, vercel, perplexity,
aws-s3, superpowers, glif, chrome-devtools, ruflo, google-calendar, gmail) should
work immediately, no edits needed.

## 4. Agents, skills, claude-flow config

Already in place relative to this repo root:
- `.claude/agents/` — the full custom agent set
- `.claude-flow/` — runtime config (`config.yaml`), capabilities, metrics
- `skills/graphify/` — copy this into `%USERPROFILE%\.claude\skills\graphify` if you
  want the `/graphify` skill available globally rather than just in this project

```
xcopy /E /I skills\graphify %USERPROFILE%\.claude\skills\graphify
```

## 5. Hooks

`smart-prompt-hook.ps1` and `session-end-hook.ps1` live at the repo root and are
wired up via `global/settings.json`. Two notes:

- `smart-prompt-hook.ps1` calls `ruflo` via PATH — make sure the global npm install
  put it there (`npm install -g` normally does).
- `session-end-hook.ps1` writes to a personal Obsidian vault
  (`~\Documents\Ideaverse\Calendar\Daily`). On a work PC you probably don't want
  this — either delete the `Stop` hook block from `global/settings.json` before
  copying it over, or let it silently create an unused folder (harmless, just noise).

## 6. Verify

```
claude doctor --fix
```

## What's NOT here (on purpose)

- `node_modules/` — reinstall with `npm install`
- `.claude-flow/daemon.pid`, `history.jsonl`, `ruvector.db`, `.last-cleanup` — pure
  runtime junk, regenerates on its own, not worth carrying over
