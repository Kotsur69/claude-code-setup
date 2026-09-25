# Agent Orchestration

## Where Agents Live

ECC agents ship with the **`ecc@ecc` plugin**, not in `~/.claude/agents/`.
They are invoked through the Agent tool with a plugin-scoped `subagent_type`:

```
Agent(subagent_type: "ecc:planner", prompt: "...")
```

`~/.claude/agents/` holds only the three local codebase-memory agents
(`codebase-memory`, `codebase-memory-scout`, `codebase-memory-auditor`),
which are invoked WITHOUT the `ecc:` prefix.

## Core Agents

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| ecc:planner | Implementation planning | Complex features, refactoring |
| ecc:architect | System design | Architectural decisions |
| ecc:code-architect | Feature blueprints from existing patterns | Before building into an existing codebase |
| ecc:code-explorer | Trace execution paths and dependencies | Understanding unfamiliar features |
| ecc:tdd-guide | Test-driven development | New features, bug fixes |
| ecc:code-reviewer | General code review | After writing code |
| ecc:security-reviewer | Security analysis, OWASP Top 10 | Before commits |
| ecc:code-simplifier | Clarity and consistency refactors | After a feature lands |
| ecc:silent-failure-hunter | Swallowed errors, bad fallbacks | Error-handling audits |
| ecc:performance-optimizer | Bottlenecks, bundle size, memory | Performance work |
| ecc:refactor-cleaner | Dead code cleanup | Code maintenance |
| ecc:doc-updater | Documentation and codemaps | Updating docs |
| ecc:e2e-runner | E2E testing | Critical user flows |
| ecc:build-error-resolver | Fix build/type errors | When build fails |

## Language and Framework Reviewers

Match the reviewer to the stack being changed:

| Stack | Reviewer | Build Resolver |
|-------|----------|----------------|
| TypeScript / JavaScript | ecc:typescript-reviewer | — |
| React / JSX | ecc:react-reviewer | ecc:react-build-resolver |
| Vue | ecc:vue-reviewer | — |
| Python | ecc:python-reviewer | — |
| FastAPI | ecc:fastapi-reviewer | — |
| Django | ecc:django-reviewer | ecc:django-build-resolver |
| PyTorch | — | ecc:pytorch-build-resolver |
| Go | ecc:go-reviewer | ecc:go-build-resolver |
| Rust | ecc:rust-reviewer | ecc:rust-build-resolver |
| Java | ecc:java-reviewer | ecc:java-build-resolver |
| Kotlin | ecc:kotlin-reviewer | ecc:kotlin-build-resolver |
| Swift | ecc:swift-reviewer | ecc:swift-build-resolver |
| C++ | ecc:cpp-reviewer | ecc:cpp-build-resolver |
| C# | ecc:csharp-reviewer | — |
| F# | ecc:fsharp-reviewer | — |
| PHP | ecc:php-reviewer | — |
| Flutter / Dart | ecc:flutter-reviewer | ecc:dart-build-resolver |
| SQL / PostgreSQL | ecc:database-reviewer | — |

> Mati's default stack: **frontend = React/Next.js/TypeScript**
> (`ecc:react-reviewer` + `ecc:typescript-reviewer`),
> **backend/ML = Python** (`ecc:python-reviewer`, `ecc:fastapi-reviewer`).

## Specialist Agents

| Agent | Purpose |
|-------|---------|
| ecc:a11y-architect | WCAG 2.2 accessibility compliance |
| ecc:type-design-analyzer | Type encapsulation and invariants |
| ecc:comment-analyzer | Comment accuracy and rot risk |
| ecc:pr-test-analyzer | PR test coverage quality |
| ecc:mle-reviewer | ML pipelines, training, serving |
| ecc:rag-pipeline-reviewer | RAG retrieval quality and chunking |
| ecc:seo-specialist | Technical SEO audits |
| ecc:marketing-agent | Campaign planning and copy |
| ecc:spec-miner | Extract specs from brownfield code |
| ecc:harness-optimizer | Agent harness reliability and cost |

For the full roster, run `/ecc:ecc-guide`.

## Immediate Agent Usage

No user prompt needed:

1. Complex feature requests — use **ecc:planner**
2. Code just written/modified — use **ecc:code-reviewer**
3. Bug fix or new feature — use **ecc:tdd-guide**
4. Architectural decision — use **ecc:architect**

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. ecc:security-reviewer - Security analysis of auth module
2. ecc:performance-optimizer - Performance review of cache system
3. ecc:typescript-reviewer - Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Delegation Completion Contract

Applies to every agent at every depth (parent, child, grandchild):

1. **Your final message IS the deliverable.** Never end your turn with "waiting for background agents" — a spawned task is not a completed task. Ending your turn while children are running orphans their results (completed children cannot notify a parent whose turn has ended).
2. **If you delegate, you own collection.** Wait for results, integrate them, then return. Fire-and-forget delegation is forbidden.
3. **Decompose only when the work cannot fit in one context.** Do not re-delegate a task already sized for a single agent — depth is an outcome, not a plan.

> Rationale: observed failure mode — research agents followed "Parallel Task Execution" above, spawned children, and returned "waiting" as their final answer. All children completed successfully but their results were orphaned. The parallel rule without a completion contract produces zombie tasks.

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:

- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
