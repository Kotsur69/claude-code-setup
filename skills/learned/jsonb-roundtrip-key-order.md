---
name: jsonb-roundtrip-key-order
description: "Postgres JSONB doesn't preserve key insertion order — JSON.stringify diffing gives false positives; use an order-independent deep-equal"
user-invocable: false
origin: auto-extracted
---

# Postgres JSONB Round-Trip Breaks JSON.stringify Equality Checks

**Extracted:** 2026-08-10
**Context:** Any app that stores a JS object in a Postgres `jsonb` column and later reads it back to decide "did anything actually change" (dirty-check before update, versioning, audit diffing, optimistic UI, caching).

## Problem

Postgres `jsonb` does **not** guarantee the same key order you wrote it with — it's a binary decomposed format. Code that writes an object, then later reads it back and diffs it with `JSON.stringify(a) === JSON.stringify(b)` produces false positives: identical data compares as "changed" purely because key order differs, even though nothing was actually edited.

In this project this surfaced while adding offer versioning: a PUT handler needed to detect "did the user actually change offer_data" to decide between updating in place vs. inserting a new version row. Comparing `JSON.stringify(existing.offer_data) === JSON.stringify(offer_data)` would have created a spurious new version on every single save, even re-saving without touching anything.

## Solution

Never use `JSON.stringify` equality on a value that has round-tripped through `jsonb`. Write a small order-independent recursive deep-equal instead:

```typescript
function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  }
  const aObj = a as Record<string, unknown>;
  const bObj = b as Record<string, unknown>;
  const aKeys = Object.keys(aObj);
  const bKeys = Object.keys(bObj);
  return (
    aKeys.length === bKeys.length &&
    aKeys.every((k) => Object.prototype.hasOwnProperty.call(bObj, k) && deepEqual(aObj[k], bObj[k]))
  );
}
```

Use it wherever "before" comes from a JSONB column and "after" is a fresh JS object (or vice versa):

```typescript
const unchanged = existing.offer_name === name && deepEqual(existing.offer_data, offer_data);
if (unchanged) {
  // plain UPDATE
} else {
  // real change -> versioning / audit / dirty-save logic
}
```

## When to Use

Fires whenever code:
- Reads a `jsonb`/`json` column back from Postgres, **and**
- Compares it against another JS object using `JSON.stringify(x) === JSON.stringify(y)` (or `===` on stringified values), **and**
- The comparison result drives a real branch (skip update, create new version, mark dirty, skip a webhook, etc.)

Same risk applies to any storage layer that doesn't preserve object key order on round-trip (MongoDB drivers, some ORMs, Redis JSON modules) — the fix (order-independent deep-equal) is identical.

Not needed when both sides of the comparison are freshly constructed in the same process without a DB round-trip in between (there, key order is stable and `JSON.stringify` is fine).
