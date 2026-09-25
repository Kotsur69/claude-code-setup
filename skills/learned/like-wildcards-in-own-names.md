---
name: like-wildcards-in-own-names
description: "Escapuj _ i % przed LIKE/ILIKE — parametryzacja nie chroni przed semantyką wildcardów we własnych nazwach typu offer_30."
user-invocable: false
origin: auto-extracted
---

# Escapuj `_` i `%`, gdy sam generujesz nazwy, które je zawierają

**Extracted:** 2026-07-14
**Context:** Wyszukiwanie `LIKE` / `ILIKE` po nazwach, które aplikacja generuje sama (fallbacki, slugi, klucze, kody typu `offer_30`, `INV_2026_01`).

## Problem

W `LIKE`/`ILIKE` znak `_` znaczy **dowolny pojedynczy znak**, a `%` **dowolny ciąg**.
Nasza nazwa zastępcza to `offer_<ID>` — czyli podkreślnik jest w **każdej** nazwie,
którą sami produkujemy.

```sql
SELECT display_name ILIKE '%offer_14%';  -- true także dla 'offerA14', 'offerX14'
```

Szukanie `offer_14` łapało `offerA14`. Cicho, bez błędu — po prostu za dużo wyników.

Ważne: **to nie jest SQL injection.** Zapytania były parametryzowane (`$1`), a mimo to
semantyka wildcardów psuła wyniki. Parametryzacja chroni przed wstrzyknięciem,
nie przed znaczeniem znaków wewnątrz wzorca.

Początkowo oceniłem to jako LOW („user raczej nie wpisze podkreślnika"). To była
zła ocena — trigger to nie „user wpisze dziwny znak", tylko **„sam generuję nazwy
z wildcardem w środku"**, co dzieje się zawsze.

## Solution

Escapuj metaznaki wzorca po stronie serwera, zanim wartość trafi do parametru:

```ts
// lib/search.ts
export function escapeLikePattern(phrase: string): string {
  return phrase.replace(/[\\%_]/g, (char) => `\\${char}`);
}

// użycie — parametryzacja zostaje, dochodzi escapowanie
params.push(escapeLikePattern(q));
// ... WHERE display_name ILIKE '%' || $1 || '%'
```

Backslash to domyślny escape w Postgresie, więc `ESCAPE` nie jest potrzebny.
Kolejność w regexie ma znaczenie: `\\` musi być pierwszy, inaczej podwójnie
uciekniesz własne backslashe.

## When to Use

- dowolne `LIKE`/`ILIKE` z frazą od usera — **zawsze**
- ze szczególną uwagą, gdy aplikacja generuje identyfikatory zawierające `_` lub `%`
  (fallbacki `offer_<id>`, slugi, kody dokumentów, klucze i18n)

Weryfikacja na żywej bazie, nie na oko: porównaj
`SELECT 'offerA14' ILIKE '%offer\_14%'` (musi być `f`) z
`SELECT 'offer_14' ILIKE '%offer\_14%'` (musi być `t`).

Powiązane: [[generated-column-round-trip]] — ten sam feature, pierwsza pułapka.
