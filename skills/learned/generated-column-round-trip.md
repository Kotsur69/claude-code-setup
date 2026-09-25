---
name: generated-column-round-trip
description: "Nigdy nie odsyłaj do API wartości z kolumny generowanej — trzymaj osobno to, co user wpisał, i to, co pokazujesz."
user-invocable: false
origin: auto-extracted
---

# Nie odsyłaj do bazy wartości, którą baza sama wylicza

**Extracted:** 2026-07-14
**Context:** Kolumny generowane / computed (Postgres `GENERATED ... STORED`, widoki, pola liczone w ORM), gdzie UI pokazuje wartość wyliczoną, a formularz pozwala edytować wartość źródłową.

## Problem

Baza wylicza nazwę wyświetlaną z nazwy własnej:

```sql
display_name GENERATED ALWAYS AS
  (COALESCE(NULLIF(TRIM(offer_name), ''), 'offer_' || id::text)) STORED
```

Front trzymał `display_name` w jednym stanie (`currentOfferName`) i odsyłał go
w PUT jako `offer_name`. Skutki:

1. Oferta bez nazwy własnej po ponownym zapisie dostawała **na stałe**
   `offer_name = 'offer_14'` — fallback zamieniał się w prawdziwą nazwę.
2. Nazwy **nie dało się wyczyścić** — puste pole wracało do starej wartości.

Błąd jest **niewidoczny w UI**, bo `COALESCE` zwraca dokładnie ten sam string,
który był pokazany wcześniej. Nic nie miga, nic nie rzuca błędu. Wykryty dopiero
przez czytanie kodu i `SELECT offer_name, display_name FROM offers` na żywej bazie
(`offer_name` NIE było `NULL`, choć nikt nazwy nie wpisał).

## Solution

Trzymaj **dwa osobne stany** i nigdy ich nie scalaj:

- `raw` = to, co user faktycznie wpisał (`''` = nie wpisał nic → `NULL` w bazie)
- `display` = to, co pokazujemy (wartość z kolumny generowanej) — **tylko do odczytu**

Do API leci wyłącznie `raw`. `display` nigdy nie wraca na serwer.

## Example

```ts
// Dwie osobne nazwy, bo znaczą co innego:
//   currentOfferName    = display_name z bazy (nazwa własna ALBO "offer_<ID>") — tylko do pokazania.
//   currentOfferRawName = to, co handlowiec naprawdę wpisał ('' = nie wpisał nic).
const [currentOfferName, setCurrentOfferName] = useState<string>('');
const [currentOfferRawName, setCurrentOfferRawName] = useState<string>('');

// load / po zapisie:
setCurrentOfferName(offer.display_name);
setCurrentOfferRawName(offer.offer_name ?? '');

// zapis — NIGDY nie wysyłaj display_name:
const name = saveOfferName.trim() || currentOfferRawName.trim();
```

Kontrolowany input też musi bindować się do `raw`, nie do `display`:
`value={saveOfferName}`, **nie** `value={saveOfferName || currentOfferName}`.

## When to Use

Zapala się, gdy w kodzie widzę którykolwiek z tych sygnałów:

- kolumna `GENERATED`, computed field, wartość z widoku SQL albo `COALESCE(x, fallback)`
  serwowana do frontu obok swojego źródła
- ten sam kawałek stanu jest jednocześnie wyświetlany **i** wysyłany w PUT/PATCH
- fallback/domyślna wartość produkowana serwerowo trafia do edytowalnego pola formularza

Test, który to łapie: **zapisz rekord dwa razy bez dotykania pola, potem wyczyść pole.**
Wartość źródłowa musi zostać `NULL`, a nie zamienić się w fallback.
Typy tego nie wykryją — `tsc` przechodzi czysto, bo obie wartości to `string`.

Powiązane: [[like-wildcards-in-own-names]] — ten sam feature, druga pułapka.
