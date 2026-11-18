# Changelog

All notable changes to PMAI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.1.0] - 2026-11-18

This release adds a third table kind for UI components and prepares the project
for a public release.

### Added

- **Components table kind.** Projects can now contain a table named
  *Components* alongside *Menu* and *Data fields* tables.
- **Component row types:** `Button`, `TextBox`, `Text Area`, `Table`, `Tabs`,
  and `H1` through `H6`. Component rows use a fixed, read-only type picker so
  the hierarchy stays consistent.
- **Text input components.** `TextBox` and `Text Area` are available in the
  fixed component type picker, with their own canvas chips and brief output.
- **Tabs component.** `Tabs` is available for tab bars and tabbed sections,
  including `tab`, `tab bar`, and `tab group` aliases.
- **New data field types.** `Enum` and `DropDown` are built-in field types with
  their own canvas chips, suitable for fixed option lists and select menus.
- **Component editor UI.** The table editor has a new *Components* kind button,
  component-specific hints, and type-aware row editing.
- **Component cards on the canvas.** Component tables use their own teal badge
  and row chips, and show the correct component type for every row.
- **Component tables in the AI brief.** The generated Markdown now includes
  component counts, interpretation rules, a dedicated component section,
  component types, notes, links, and build-checklist items.
- **Component linking.** A component row can still link to another table, so
  arrows and the link map work exactly like menu and field rows.
- **Live component counts** in the status bar.
- **Component normalization.** Hand-edited projects and imported files are
  repaired automatically: `button`, `text box`, `textarea`, `tab bar`,
  `heading 1`, `data table`, and similar spellings are converted to canonical
  component types.
- **New tests** covering component normalization, the table and row dialogs,
  the AI brief, and status-bar counts.
- **Public-release documentation:** a rewritten `README.md`, a complete
  `FEATURES.md`, and this `CHANGELOG.md`.

### Changed

- The project file format is now **version 2**. Version 1 files still open
  normally; version 2 files require PMAI 1.1 or newer.
- The table editor is slightly wider so the three kind buttons fit comfortably.
- The **+ Add row** button is now a solid primary button with bold text, making it
  easier to spot next to Edit, Duplicate, and Remove.
- Quick-start, About, empty-state, README, and dialog copy now describe
  components as a first-class table kind.
- The package version is now `1.1.0`.

### Fixed

- Switching a table to *Data fields* now also converts component rows to text
  fields, not just menu rows.
- Switching table kinds preserves row links in every direction.

### Compatibility

- `.pmproj` and `.bin` files saved by PMAI 1.0 load without changes.
- Files saved by PMAI 1.1 use format version 2 and will be rejected by PMAI 1.0
  with a clear "newer version" message instead of silently misreading
  component tables as field tables.

## [1.0.0] - 2026-11-18

Initial release.

### Added

- Offline desktop sketcher for app structure.
- Menu and modal / database-field tables.
- 22 built-in field types plus custom types.
- Row-to-table links with curved arrows.
- Drag-to-move cards, wheel scroll, middle-drag pan, and Ctrl+wheel zoom.
- Automatic layout and fit-to-view.
- AI brief generation as Markdown.
- Undo / redo and unsaved-state tracking.
- Readable `.pmproj` JSON and compressed `.bin` project files.
- Windows launchers and a PyInstaller build script.
