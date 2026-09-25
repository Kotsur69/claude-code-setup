---
name: postgres-for-update-no-aggregate
description: "SELECT ... FOR UPDATE errors when combined with an aggregate (MAX/COUNT/SUM) — lock plain rows, aggregate in application code"
user-invocable: false
origin: auto-extracted
---

# Postgres Forbids FOR UPDATE Combined with Aggregate Functions

**Extracted:** 2026-08-10
**Context:** Any transaction that needs to (a) lock a set of rows against concurrent writes, and (b) compute a MAX/COUNT/SUM/etc. over that same set before inserting or updating — e.g. computing "next sequence number in a family of rows."

## Problem

Postgres rejects `SELECT ... FOR UPDATE` when the query also uses an aggregate function or `GROUP BY`:

```sql
-- ERROR: FOR UPDATE is not allowed with aggregate functions
SELECT COALESCE(MAX(version_number), 0) AS max_version
FROM offers WHERE id = $1 OR root_offer_id = $1
FOR UPDATE;
```

This surfaced while implementing offer versioning: locking a family of rows (root + its versions) to safely compute "next version number" under concurrent saves. The natural-looking single query throws at runtime — `tsc` and any static check pass cleanly, because it's a Postgres-level restriction, not a type error. It only shows up the first time the code path actually executes.

## Solution

Split into two steps: lock the **plain rows** with `FOR UPDATE` (no aggregate), then compute the aggregate in application code over the returned rows.

```typescript
// Locks the rows so a concurrent save on the same family can't race past us.
const versionResult = await db.query(
  `SELECT version_number FROM offers WHERE id = $1 OR root_offer_id = $1 FOR UPDATE`,
  [rootId]
);
const nextVersion =
  Math.max(0, ...versionResult.rows.map((r) => Number(r.version_number))) + 1;
```

The lock still does its job (concurrent transactions block on the same rows until commit) — it just moves the arithmetic out of SQL and into application code.

## When to Use

Fires whenever a query combines:
- `FOR UPDATE` (or `FOR NO KEY UPDATE`, `FOR SHARE`, etc.), **and**
- `MAX()`, `MIN()`, `COUNT()`, `SUM()`, `AVG()`, or `GROUP BY`

on the same `SELECT`. The fix is always the same shape: drop the aggregate from the locking query, pull back the raw rows, reduce them in application code.
