# PMAI Features

PMAI (**Project → Prompt**) is a local-first desktop sketcher for app structure.
You draw the pieces of an application — navigation, data models, and UI
components — and PMAI turns that diagram into a precise Markdown brief for an AI
coding assistant.

This document lists everything the app can do. For a short overview, see
[README.md](README.md). For release history, see [CHANGELOG.md](CHANGELOG.md).

## Three table kinds

Every card on the canvas is a table. Tables describe one part of the app.

| Kind | Purpose | Row types | Card badge |
| --- | --- | --- | --- |
| **Menu** | Sidebar entries, navigation, nested pages | `Menu` (fixed) | Amber `MENU` |
| **Data fields** | Database models, forms, modals, detail views | 24 field types plus custom text | Blue `FIELDS` |
| **Components** | Reusable UI building blocks and headings | `Button`, `TextBox`, `Text Area`, `Table`, `Tabs`, `H1`–`H6` | Teal `COMPONENTS` |

You can change a table's kind at any time. PMAI asks before converting existing
rows and keeps all row links.

## Component types

Component tables use a fixed, read-only type picker:

| Type | Meaning |
| --- | --- |
| `Button` | An interactive action such as Save, Submit, or New invoice |
| `TextBox` | A single-line text input |
| `Text Area` | A multi-line text input for notes, descriptions, or messages |
| `Table` | A data grid, list, or results table |
| `Tabs` | A tab bar or tabbed section for switching views |
| `H1` | The largest page heading |
| `H2` | Section heading |
| `H3` | Subsection heading |
| `H4`–`H6` | Deeper heading levels |

This keeps component diagrams predictable. The AI brief tells the receiving
assistant to build real semantic heading levels and to treat buttons, text
inputs, tables, and tabs as actual UI elements, not just labels.

Hand-edited project files are repaired automatically. For example, `button`,
`text box`, `textarea`, `heading 1`, `data table`, and `tab bar` become
`Button`, `TextBox`, `Text Area`, `H1`, `Table`, and `Tabs`.

## Field types

Field tables support 24 built-in types:

`Text`, `Long Text`, `Number`, `Integer`, `Decimal`, `Currency`, `Boolean`,
`Date`, `Time`, `DateTime`, `Email`, `Phone`, `URL`, `Select`, `Multi Select`,
`Enum`, `DropDown`, `Auto ID`, `Reference`, `File`, `Image`, `Password`, `JSON`,
and `Formula`.

You can also type any custom field type, such as `Rating (1–5)` or `Color`.

## Rows, notes, and links

- Every row has a **name**, **type**, and **notes**.
- Every table has optional **table notes** shown under the card and in the brief.
- A row can **link to another table**. PMAI draws a curved arrow from the row to
  the target card.
- Links can be created in three ways: the **Link rows** mode, the row editor, or
  the row's right-click menu.
- Menu links describe navigation. Field links describe foreign keys or detail
  views. Component links describe where a component is used or what it opens.

## Canvas and editing

- Drag anywhere on a card to move it. A small movement threshold keeps clicks
  and double-clicks working.
- Double-click a card to edit the table; double-click a row to edit the row.
- Wheel scrolls vertically, `Shift`+wheel scrolls horizontally.
- `Ctrl`+wheel zooms at the pointer. Middle-drag pans.
- **Fit** brings every table into view.
- **Arrange** lays out tables left-to-right from the link graph, including
  cycles.
- **Undo / redo** covers table creation, edits, deletion, duplication, links,
  moves, layout, and project renames.
- The title bar and header show unsaved-state and save-state indicators.

## AI brief

Press **Translate** (`Ctrl+Shift+T` or `F5`) to generate a Markdown build brief.
It contains:

1. **Project summary** — name, description, table counts, row total, top-level
   menus, and timestamp.
2. **Interpretation rules** — how to read menus, data fields, components, notes,
   and links.
3. **Menu tables** — every navigation item, type, note, and target.
4. **Modal / database-field tables** — every field, type, note, and target.
5. **Component tables** — every Button, TextBox, Text Area, Table, Tabs, and
   heading with its level, notes, and target.
6. **Link map** — source table, source row, target table, and target kind.
7. **Build checklist** — ordered implementation tasks derived from the diagram.

Your notes are quoted in full. The brief explicitly tells the AI not to invent
screens, fields, components, or business rules that are not in the diagram.

## Project files

| Format | Description |
| --- | --- |
| `.pmproj` | Human-readable JSON. Good for backups, diffs, and hand editing. |
| `.bin` | Gzip-compressed JSON with a `PMAI-BIN` magic header. Smaller files. |
| `.md` | Exported AI build brief (not a project file). |

Saving is atomic: PMAI writes a temporary file and replaces the old project only
after the write succeeds. Opening detects the format from the file contents, so
either extension works.

Projects store the name, description, timestamps, every table's
kind/name/notes/position, and every row's name/type/notes/link. IDs are stable
across saves.

## Privacy and offline use

- No accounts, telemetry, network calls, or database server.
- No Python packages are needed at runtime; everything uses the standard library.
- PMAI reads and writes only the files you choose.
- The clipboard is touched only when you press **Copy brief**.
- `run.bat` and `build.bat` contact the internet only during first-time setup or
  when installing PyInstaller.

## Platform

- Designed for Windows 10 and 11.
- Python 3.10 or newer with Tkinter.
- Launchers can install Python 3.12 for the current user if it is missing.
- A PyInstaller build produces a single-file, console-free `PMAI.exe`.

## What's new in 1.1

- New **Components** table kind.
- New `Button`, `TextBox`, `Text Area`, `Table`, `Tabs`, and `H1`–`H6` row types.
- New `Enum` and `DropDown` data field types.
- Component cards, counts, editor hints, normalization, and AI-brief support.
- Project format version 2, with backward-compatible loading of version 1 files.
- Expanded tests and refreshed public documentation.

See [CHANGELOG.md](CHANGELOG.md) for the complete list.

## Known limitations

- Windows is the primary supported platform. The Python source may run on other
  systems with Tkinter, but the launchers are PowerShell scripts.
- Links always target a whole table, not a specific row or column.
- The canvas caps very large tables at 14 visible rows; open the table editor to
  see the rest.
- There is no built-in export to images or PDF yet.

## Possible next steps

- More component types (cards, alerts, navigation bars, accordions).
- Optional row-level cross-references inside the brief.
- Image / PDF export of the diagram.
- A component-only starter sample project.
- Additional themes and accessibility settings.
