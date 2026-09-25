---
name: docx-report-editing
description: "Dopisywanie wierszy do tabel .docx przez deepcopy wiersza (python-docx) — add_row gubi formatowanie; ~$plik = otwarty Word."
user-invocable: false
origin: auto-extracted
---

# Edycja raportów .docx bez gubienia formatowania (python-docx)

**Extracted:** 2026-07-14
**Context:** AMSteel_Quote — raporty wersji dla zarządu w `Historia wersji oraz md/Historia wersji/AMSteel_Quote_Raport_Wersji_*.docx`. Dopisywanie zmian do istniejących tabel dokumentu Worda.

## Problem

`table.add_row()` w `python-docx` tworzy wiersz o **domyślnym** formatowaniu, nie takim
jak reszta tabeli — czcionka, obramowania i cieniowanie się rozjeżdżają. W dokumencie,
który idzie do zarządu, to widać od razu.

Druga pułapka: plik `~$Nazwa.docx` w folderze oznacza **otwarty Word**. Word trzyma
dokument w pamięci i przy zapisie **nadpisze** twoje zmiany starą wersją — po cichu.

## Solution

Klonuj istniejący wiersz przez `deepcopy` na poziomie XML i podmień tylko tekst:

```python
import copy
from docx import Document

def append_row(table, *values):
    """Klonuje ostatni wiersz danych (zachowuje styl) i podmienia tekst."""
    template = table.rows[-1]._tr
    new_tr = copy.deepcopy(template)
    template.addnext(new_tr)
    row = table.rows[-1]
    for cell, text in zip(row.cells, values):
        para = cell.paragraphs[0]
        for extra in cell.paragraphs[1:]:          # zostaw jeden akapit
            extra._element.getparent().remove(extra._element)
        for extra_run in para.runs[1:]:            # zostaw jeden run (nosi styl)
            extra_run._element.getparent().remove(extra_run._element)
        if para.runs:
            para.runs[0].text = text               # NIE add_run — tracisz formatowanie
        else:
            para.add_run(text)
```

Klucz: pisz w **istniejący run**, nie dodawaj nowego. Run niesie formatowanie znaków.

## Workflow

1. `ls` folderu — jeśli jest `~$*.docx`, ostrzeż usera, żeby zamknął Worda przed zapisem.
2. Kopia zapasowa: `cp raport.docx raport_backup_przed_<czym>.docx` (repo trzyma takie kopie).
3. Zrzuć strukturę przed edycją — tabele nie mają nazw, trzeba je zidentyfikować po treści:
   ```python
   for ti, t in enumerate(doc.tables):
       print(f'=== TABLE {ti}')
       for r in t.rows:
           print(' | '.join(c.text.strip() for c in r.cells))
   ```
4. Edytuj, zapisz, **zweryfikuj ponownym odczytem** (`doc.tables[i].rows[-4:]`).

Konsola Windows psuje polskie znaki przy wypisywaniu — uruchamiaj `python -X utf8`
i `sys.stdout.reconfigure(encoding='utf-8')`. Mojibake w terminalu ≠ zepsuty plik.

## When to Use

Gdy user prosi o aktualizację raportu wersji / changeloga w `.docx`, albo o dopisanie
wierszy do tabeli w dokumencie Worda. Struktura raportu 1.3: tabela 0 = metryka,
tabela 1 = historia wersji, tabele 2–6 = zmiany wg obszaru (systemowe, kalkulator,
oferty, PDF, interfejs), tabela 7 = podpisy.
