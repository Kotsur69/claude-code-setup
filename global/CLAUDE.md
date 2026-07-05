# Ruflo Integration — Automatic Tool Protocol

## ALWAYS do this before responding to any non-trivial task:
1. Check system-reminder for `[INTELLIGENCE]` routing suggestions — follow them
2. Call `mcp__ruflo__memory_search` with task keywords to find relevant past patterns
3. If the task involves a known project → query graphify before touching any file
4. If 3+ files will change → call `mcp__ruflo__hooks_route` to determine optimal agent topology

## ALWAYS do this after a successful task:
5. Call `mcp__ruflo__memory_store` with what worked (namespace: patterns)
6. Call `mcp__ruflo__hooks_post-task` with outcome=success

## Automatic tool triggers (no user command needed):
- User mentions "test", "testing", "sprawdź" → search memory for test patterns + check graphify for test files
- User mentions a project name → immediately load its graphify GRAPH_REPORT.md
- User mentions "security", "auth", "credentials" → run `mcp__ruflo__aidefence_scan` on relevant code
- User asks "what", "how", "why" about code → run graphify query first, not file browsing
- Task involves 3+ files → spawn appropriate swarm topology via `mcp__ruflo__swarm_init`
- User mentions "performance", "slow", "optimize" → use performance-engineer agent

Key tools: memory_store, memory_search, hooks_route, swarm_init, agent_spawn, aidefence_scan.
Use ToolSearch("keyword") to discover exact MCP tool names before calling.
# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# Project Context Auto-Load

When the user mentions working on any of these projects, immediately read the listed files before responding — no need to be asked:

## Synthara
Path: `C:\Users\Kotsur69\.local\bin\synthara`
- Read: `CLAUDE.md` (architecture rules)
- Read: `graphify-out\GRAPH_REPORT.md` (god nodes, communities, surprises)
- Read: `graphify-out\.graphify_analysis.json` (for graph queries)

## Luna Voice
Path: `C:\Users\Kotsur69\source\repos\luna-voice`
- Read: `CLAUDE.md`
- Read: `graphify-out\GRAPH_REPORT.md`

## Luna V (Active Luna project)
Path: `C:\Users\Kotsur69\source\repos\LUNA V`

## Crypto Trading Bot
Path: `C:\Users\Kotsur69\source\repos\crypto_trading_bot-20260407T164341Z-3-001`
- Read: `CLAUDE.md`
- Read: `graphify-out\GRAPH_REPORT.md`

## New Large Projects (auto-setup rule)
When the user starts working on a **new large project** (3+ files, new feature area, or names it as a project):
1. Run graphify on it: full pipeline as per the graphify skill
2. Run `graphify claude install` in the project directory
3. Add the project to this section in `C:\Users\Kotsur69\.claude\CLAUDE.md` with its path and key files
4. Add a MOC note to `C:\Users\Kotsur69\Documents\Ideaverse\Atlas\Maps\`
5. Update `C:\Users\Kotsur69\.claude\projects\C--Users-Kotsur69--local-bin\memory\user_preferences.md` with the new project
