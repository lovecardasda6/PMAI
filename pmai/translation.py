"""Turn the visual diagram into a precise, AI-friendly build brief."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import KIND_SHORT_LABELS, Project, Table


def _clean(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _cell(text: str) -> str:
    """Escape a value for a Markdown table cell."""
    value = _clean(text)
    if not value:
        return "—"
    value = value.replace("\\", "\\\\").replace("|", "\\|")
    return value.replace("\n", "<br>")


def _inline(text: str) -> str:
    return _clean(text).replace("\n", " ")


def _row_link(row, table_lookup: dict[str, Table]) -> str:
    target = table_lookup.get(row.link_table_id or "")
    if not target:
        return "—"
    return f"{_inline(target.name)} ({KIND_SHORT_LABELS.get(target.kind, target.kind)})"


def _notes_line(prefix: str, notes: str, out: list[str]) -> None:
    text = _clean(notes)
    if not text:
        return
    lines = text.splitlines() or [text]
    out.append(f"**{prefix}:**")
    out.append("")
    for line in lines:
        out.append(f"> {line}".rstrip() if line else ">")
    out.append("")


def _brief_empty() -> str:
    return (
        "# AI Build Brief\n\n"
        "This project does not contain any tables yet.\n\n"
        "Add a **Menu** table for navigation, a **Modal / Fields** table for a "
        "data model, or a **Page** table for a screen made of reusable UI "
        "components, and describe each item. Then generate this brief again.\n"
    )


def build_ai_brief(
    project: Project,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Build a deterministic Markdown prompt from the current project."""
    if not project.tables:
        return _brief_empty()

    generated_at = generated_at or datetime.now(timezone.utc)
    table_lookup = {table.id: table for table in project.tables}
    menu_tables = project.menu_tables()
    field_tables = project.field_tables()
    page_tables = project.page_tables()
    roots = project.root_menu_tables()
    incoming = project.incoming_links()

    out: list[str] = []
    out.append(f"# AI Build Brief — {_inline(project.name) or 'Untitled Project'}")
    out.append("")
    out.append(
        "You are an AI software engineer. Use this document as the **source of "
        "truth** for building the application. The tables below were designed "
        "visually by the user; rows and notes are requirements, not suggestions."
    )
    out.append("")
    out.append("## 1. Project summary")
    out.append("")
    out.append(f"- **Project:** {_inline(project.name) or 'Untitled Project'}")
    if _clean(project.description):
        out.append(f"- **Description:** {_inline(project.description)}")
    out.append(f"- **Menu tables:** {len(menu_tables)}")
    out.append(f"- **Modal / field tables:** {len(field_tables)}")
    out.append(f"- **Page tables:** {len(page_tables)}")
    out.append(f"- **Rows total:** {project.total_rows()}")
    if roots:
        names = ", ".join(_inline(t.name) for t in roots)
        out.append(f"- **Top-level menu tables:** {names}")
    out.append(
        f"- **Generated:** {generated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    out.append("")

    out.append("## 2. Interpretation rules")
    out.append("")
    out.append(
        "1. **Menu tables** describe navigation. Every row in a menu table is a "
        "menu item (`Type` = `Menu`)."
    )
    out.append(
        "2. A menu row linked to another **menu** table opens that menu as a "
        "nested page / section."
    )
    out.append(
        "3. A menu row linked to a **modal/fields** table opens that data view "
        "(modal, drawer, or dedicated page — choose the most appropriate pattern)."
    )
    out.append(
        "4. A menu row linked to a **page** table opens that page."
    )
    out.append(
        "5. **Modal / fields tables** define data models and the forms that edit "
        "them. Treat each row as a field and its type as the storage/input type."
    )
    out.append(
        "6. **Page tables** describe screens built from reusable UI components. "
        "Every row is one component, typed as `Button`, `TextBox`, `Text Area`, "
        "`DropDown`, `Radio Button`, `Checkbox`, `Toggle`, `Date Picker`, "
        "`Number Input`, `Search`, `Slider`, `File Upload`, `Table`, or `Tabs`. "
        "Build the matching interactive control with accessible labels and "
        "validation where relevant."
    )
    out.append(
        "7. Follow every table note and row note exactly. Notes may add behavior, "
        "defaults, or placement instructions that are not visible in the columns."
    )
    out.append(
        "8. Keep labels and spelling as written. Do **not** invent menu items, "
        "fields, components, screens, or business rules that are not described here."
    )
    out.append(
        "9. Top-level menu tables (those with no incoming links) are the primary "
        "navigation entry points, normally rendered as a sidebar."
    )
    out.append("")

    section = 3
    out.append(f"## {section}. Menu tables (navigation)")
    out.append("")
    if not menu_tables:
        out.append("_No menu tables were defined._")
        out.append("")
    for index, table in enumerate(menu_tables, start=1):
        links_in = incoming.get(table.id, [])
        out.append(f"### {section}.{index} {_inline(table.name) or 'Untitled table'}")
        out.append("")
        out.append("- **Kind:** Menu")
        out.append(
            "- **Incoming links:** "
            + (
                ", ".join(f"{_inline(src.name)} / {_inline(row.name)}" for src, row in links_in)
                if links_in
                else "None (top-level navigation)"
            )
        )
        out.append("")
        _notes_line("Table notes", table.notes, out)
        out.append("| Menu item | Type | Notes | Links to |")
        out.append("| --- | --- | --- | --- |")
        if table.rows:
            for row in table.rows:
                out.append(
                    f"| {_cell(row.name)} | Menu | {_cell(row.notes)} | "
                    f"{_cell(_row_link(row, table_lookup))} |"
                )
        else:
            out.append("| _No rows_ | — | — | — |")
        out.append("")

    section += 1
    out.append(f"## {section}. Modal / database-field tables")
    out.append("")
    if not field_tables:
        out.append("_No modal or database-field tables were defined._")
        out.append("")
    for index, table in enumerate(field_tables, start=1):
        links_in = incoming.get(table.id, [])
        out.append(f"### {section}.{index} {_inline(table.name) or 'Untitled table'}")
        out.append("")
        out.append("- **Kind:** Modal / Fields")
        out.append(
            "- **Incoming links:** "
            + (
                ", ".join(f"{_inline(src.name)} / {_inline(row.name)}" for src, row in links_in)
                if links_in
                else "None"
            )
        )
        out.append("")
        _notes_line("Table notes", table.notes, out)
        out.append("| Field | Type | Notes | Links to |")
        out.append("| --- | --- | --- | --- |")
        if table.rows:
            for row in table.rows:
                out.append(
                    f"| {_cell(row.name)} | {_cell(row.type)} | {_cell(row.notes)} | "
                    f"{_cell(_row_link(row, table_lookup))} |"
                )
        else:
            out.append("| _No fields_ | — | — | — |")
        out.append("")

    section += 1
    out.append(f"## {section}. Page tables (UI screens)")
    out.append("")
    if not page_tables:
        out.append("_No page tables were defined._")
        out.append("")
    for index, table in enumerate(page_tables, start=1):
        links_in = incoming.get(table.id, [])
        out.append(f"### {section}.{index} {_inline(table.name) or 'Untitled table'}")
        out.append("")
        out.append("- **Kind:** Page")
        out.append(
            "- **Incoming links:** "
            + (
                ", ".join(f"{_inline(src.name)} / {_inline(row.name)}" for src, row in links_in)
                if links_in
                else "None"
            )
        )
        out.append("")
        _notes_line("Table notes", table.notes, out)
        out.append("| Component | Type | Notes | Links to |")
        out.append("| --- | --- | --- | --- |")
        if table.rows:
            for row in table.rows:
                out.append(
                    f"| {_cell(row.name)} | {_cell(row.type)} | {_cell(row.notes)} | "
                    f"{_cell(_row_link(row, table_lookup))} |"
                )
        else:
            out.append("| _No components_ | — | — | — |")
        out.append("")

    section += 1
    out.append(f"## {section}. Link map (drawing arrows)")
    out.append("")
    links = []
    for table in project.tables:
        for row in table.rows:
            target = table_lookup.get(row.link_table_id or "")
            if target:
                links.append((table, row, target))
    if links:
        out.append("| Source table | Source row | Target table | Target kind |")
        out.append("| --- | --- | --- | --- |")
        for source, row, target in links:
            out.append(
                f"| {_cell(source.name)} | {_cell(row.name)} | {_cell(target.name)} | "
                f"{KIND_SHORT_LABELS.get(target.kind, target.kind)} |"
            )
    else:
        out.append("_No links were defined between rows and tables._")
    out.append("")

    section += 1
    out.append(f"## {section}. Build checklist")
    out.append("")
    out.append(
        "- [ ] Create the application shell and primary navigation from the "
        "top-level menu tables."
    )
    for table in menu_tables:
        out.append(f"- [ ] Build the **{_inline(table.name)}** menu screen and its items.")
    for table in field_tables:
        out.append(
            f"- [ ] Create the **{_inline(table.name)}** data model, validation, "
            "list view, and create/edit form."
        )
    for table in page_tables:
        out.append(
            f"- [ ] Build the **{_inline(table.name)}** page and add every listed "
            "button, input, choice control, table, and tab in the intended order."
        )
    if links:
        out.append(
            "- [ ] Wire every navigation and action link listed in the link map."
        )
    out.append("- [ ] Apply all table-level and row-level notes exactly.")
    out.append(
        "- [ ] Use clean, accessible UI, sensible empty/error states, and local "
        "persistence appropriate for the chosen stack."
    )
    out.append("")
    out.append("---")
    out.append("")
    out.append(
        "Ask the user before inventing missing requirements. Build the complete "
        "working application from this specification."
    )
    out.append("")
    return "\n".join(out)


def default_brief_filename(project: Project) -> str:
    safe = "".join(
        ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in project.name
    ).strip()
    safe = (safe or "project")[:80].rstrip(" .") or "project"
    return f"{safe}-ai-brief.md"
