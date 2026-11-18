"""Project editing dialogs."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..models import (
    COMPONENT_TYPES,
    COMPONENTS,
    FIELD_TYPES,
    FIELDS,
    MENU,
    MENU_ROW,
    Project,
    Row,
    Table,
    is_component_type,
    new_id,
    normalize_component_type,
)
from ..translation import default_brief_filename
from . import theme
from .widgets import (
    BaseDialog,
    FlatButton,
    field_label,
    make_entry,
    make_text,
    text_value,
)


def _one_line(text: str) -> str:
    return str(text or "").replace("\r", " ").replace("\n", " ").strip()


def _short(text: str, limit: int = 80) -> str:
    value = _one_line(text)
    return value if len(value) <= limit else value[: limit - 1] + "\u2026"


def _format_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return stamp.strftime("%d %b %Y, %H:%M UTC")


class TableDialog(BaseDialog):
    """Create or edit a menu, database-field, or component table."""

    def __init__(self, parent, project: Project, table: Table | None = None):
        creating = table is None
        self.project = project
        self._table = table.clone() if table else Table(name="", kind=MENU, notes="")
        self.rows = [row.clone() for row in self._table.rows]
        title = "New table" if creating else "Edit table"
        subtitle = (
            "Define navigation, a data model, or reusable UI components, "
            "then add its rows."
        )
        super().__init__(
            parent,
            title,
            subtitle,
            width=820,
            height=710,
        )
        self._creating = creating
        self._kind = (
            self._table.kind
            if self._table.kind in {MENU, FIELDS, COMPONENTS}
            else MENU
        )
        self._build()
        self.add_footer_button("Cancel", self._cancel)
        self._primary = self.add_footer_button(
            "Create table" if creating else "Save changes",
            self._submit,
            variant="primary",
            weight="bold",
        )
        self.footer_note.configure(text="Tip: link a row to another table to draw an arrow.")
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Control-Return>", lambda _e: self._submit())

    # ---- UI ------------------------------------------------------------

    def _build(self) -> None:
        content = tk.Frame(self.body, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=24, pady=(16, 14))

        top = tk.Frame(content, bg=theme.BG)
        top.pack(fill="x")

        name_frame = tk.Frame(top, bg=theme.BG)
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, 20))
        field_label(name_frame, "Table name").pack(fill="x", pady=(0, 6))
        self.name_var = tk.StringVar(value=self._table.name)
        self.name_entry = make_entry(name_frame, self.name_var)
        self.name_entry.pack(fill="x", ipady=6)
        self.name_entry.bind("<Return>", lambda _e: self._submit())

        kind_frame = tk.Frame(top, bg=theme.BG)
        kind_frame.pack(side="right", fill="x")
        field_label(kind_frame, "Table kind").pack(fill="x", pady=(0, 6))
        toggle = tk.Frame(kind_frame, bg=theme.BG)
        toggle.pack(fill="x")
        toggle.grid_columnconfigure(0, weight=1)
        toggle.grid_columnconfigure(1, weight=1)
        toggle.grid_columnconfigure(2, weight=1)
        self.menu_button = FlatButton(
            toggle, text="Menu", command=lambda: self._set_kind("menu"), padx=14, pady=6
        )
        self.menu_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.fields_button = FlatButton(
            toggle,
            text="Data fields",
            command=lambda: self._set_kind("fields"),
            padx=14,
            pady=6,
        )
        self.fields_button.grid(row=0, column=1, sticky="ew", padx=4)
        self.components_button = FlatButton(
            toggle,
            text="Components",
            command=lambda: self._set_kind("components"),
            padx=14,
            pady=6,
        )
        self.components_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        self.kind_hint = tk.Label(
            kind_frame,
            text="",
            bg=theme.BG,
            fg=theme.MUTED,
            font=theme.font(8),
            anchor="w",
            justify="left",
            wraplength=300,
        )
        self.kind_hint.pack(fill="x", pady=(5, 0))

        notes_head = tk.Frame(content, bg=theme.BG)
        notes_head.pack(fill="x", pady=(14, 0))
        field_label(notes_head, "Table notes").pack(side="left")
        tk.Label(
            notes_head,
            text="optional \u00b7 shown under the table",
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
        ).pack(side="left", padx=(8, 0))
        self.notes = make_text(content, height=3)
        self.notes.pack(fill="x", pady=(6, 0))
        self.notes.insert("1.0", self._table.notes)

        rows_head = tk.Frame(content, bg=theme.BG)
        rows_head.pack(fill="x", pady=(14, 6))
        field_label(rows_head, "Rows").pack(side="left")
        self.count_label = tk.Label(
            rows_head,
            text="",
            bg=theme.BG,
            fg=theme.MUTED,
            font=theme.font(8),
        )
        self.count_label.pack(side="left", padx=(8, 0))
        tools = tk.Frame(rows_head, bg=theme.BG)
        tools.pack(side="right")
        self.add_row_button = FlatButton(
            tools,
            text="+ Add row",
            command=self._add_row,
            variant="primary",
            weight="bold",
            size=9,
            padx=10,
            pady=3,
        )
        self.add_row_button.pack(side="left")
        for text, command in (
            ("Edit", self._edit_row),
            ("Duplicate", self._duplicate_row),
            ("Remove", self._remove_row),
        ):
            FlatButton(
                tools,
                text=text,
                command=command,
                variant="ghost",
                size=9,
                padx=9,
                pady=3,
            ).pack(side="left", padx=(5, 0))
        for text, command in (("\u2191", lambda: self._move_row(-1)), ("\u2193", lambda: self._move_row(1))):
            FlatButton(
                tools,
                text=text,
                command=command,
                variant="ghost",
                size=9,
                padx=7,
                pady=3,
            ).pack(side="left", padx=(5, 0))

        tree_frame = tk.Frame(
            content,
            bg=theme.SURFACE,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        tree_frame.pack(fill="both", expand=True, pady=(0, 4))
        columns = ("name", "type", "notes", "link")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Editor.Treeview",
            height=7,
        )
        headings = {
            "name": ("Name", 190),
            "type": ("Type", 105),
            "notes": ("Notes", 220),
            "link": ("Links to", 165),
        }
        for key, (label, width) in headings.items():
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=width, minwidth=70, stretch=key in {"name", "notes"})
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("odd", background=theme.SURFACE_ALT)
        self.tree.bind("<Double-Button-1>", lambda _e: self._edit_row())
        self.tree.bind("<Delete>", lambda _e: self._remove_row())
        self.tree.bind("<Return>", lambda _e: self._edit_row())
        self.tree_empty = tk.Label(
            tree_frame,
            text="No rows yet\nClick \u201c+ Add row\u201d to add the first one.",
            bg=theme.SURFACE,
            fg=theme.FAINT,
            font=theme.font(9),
            justify="center",
        )
        self.tree_empty.place(relx=0.5, rely=0.55, anchor="center")

        self._update_kind_buttons()
        self._refresh_rows()

    # ---- helpers -------------------------------------------------------

    def focus_first(self) -> None:
        self.name_entry.focus_set()

    def _kind_name(self) -> str:
        return {
            MENU: "Menu",
            FIELDS: "Data fields",
            COMPONENTS: "Components",
        }.get(self._kind, "Data fields")

    def _update_kind_buttons(self) -> None:
        for kind, button in (
            (MENU, self.menu_button),
            (FIELDS, self.fields_button),
            (COMPONENTS, self.components_button),
        ):
            button.set_variant("primary" if self._kind == kind else "ghost")
        if self._kind == MENU:
            self.kind_hint.configure(text="Every row is a navigation item (Menu).")
        elif self._kind == COMPONENTS:
            self.kind_hint.configure(
                text=(
                    "Rows are UI components: Button, TextBox, Text Area, Table, "
                    "Tabs, or H1\u2013H6."
                )
            )
        else:
            self.kind_hint.configure(text="Rows are database fields or modal inputs.")

    def _set_kind(self, kind: str) -> None:
        if kind == self._kind:
            return
        if kind == MENU:
            converts = [row for row in self.rows if row.type != MENU_ROW]
            if converts and not messagebox.askyesno(
                "Change table kind?",
                f"All {len(converts)} row(s) will become Menu navigation items. "
                "Links are kept.\n\nContinue?",
                parent=self,
            ):
                return
            for row in self.rows:
                row.type = MENU_ROW
        elif kind == COMPONENTS:
            if self.rows and not messagebox.askyesno(
                "Change table kind?",
                f"All {len(self.rows)} row(s) will become Button components. "
                "Links are kept.\n\nContinue?",
                parent=self,
            ):
                return
            for row in self.rows:
                row.type = "Button"
        else:
            converts = [
                row
                for row in self.rows
                if row.type == MENU_ROW or is_component_type(row.type)
            ]
            if converts and not messagebox.askyesno(
                "Change table kind?",
                f"{len(converts)} menu/component row(s) will become Text fields. "
                "Links are kept.\n\nContinue?",
                parent=self,
            ):
                return
            for row in converts:
                row.type = "Text"
        self._kind = kind
        self._update_kind_buttons()
        self._refresh_rows()

    def _link_label(self, row: Row) -> str:
        target = self.project.get_table(row.link_table_id)
        if not target:
            return "\u2014"
        return f"{_short(target.name, 34)} ({target.kind_short})"

    def _refresh_rows(self, select_id: str | None = None) -> None:
        if select_id is None:
            current = self.tree.selection()
            select_id = current[0] if current else None
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.rows):
            if self._kind == MENU:
                display_type = MENU_ROW
            elif self._kind == COMPONENTS:
                display_type = normalize_component_type(row.type)
            else:
                display_type = row.type
            self.tree.insert(
                "",
                "end",
                iid=row.id,
                values=(
                    _short(row.name, 34),
                    _short(display_type, 18),
                    _short(row.notes, 48),
                    self._link_label(row),
                ),
                tags=("odd",) if index % 2 else (),
            )
        self.count_label.configure(
            text=f"{len(self.rows)} row{'s' if len(self.rows) != 1 else ''}"
        )
        if self.rows:
            self.tree_empty.place_forget()
            ids = [row.id for row in self.rows]
            if select_id not in ids:
                select_id = ids[0]
            self.tree.selection_set(select_id)
            self.tree.focus(select_id)
            self.tree.see(select_id)
        else:
            self.tree_empty.place(relx=0.5, rely=0.55, anchor="center")
            self.tree_empty.lift()

    def _selected_row(self) -> Row | None:
        selection = self.tree.selection()
        if not selection:
            return None
        row_id = selection[0]
        for row in self.rows:
            if row.id == row_id:
                return row
        return None

    def _show_note(self, text: str, tone: str = "muted") -> None:
        self.footer_note.configure(
            text=text,
            fg=theme.DANGER if tone == "error" else theme.MUTED,
        )

    def _targets(self) -> list[Table]:
        return [t for t in self.project.tables if t.id != self._table.id]

    def _row_dialog(self, row: Row | None) -> RowDialog:
        return RowDialog(
            self,
            row=row,
            table_kind=self._kind,
            targets=self._targets(),
            title="Add row" if row is None else "Edit row",
        )

    def _add_row(self) -> None:
        row = self._row_dialog(None).show()
        if row is not None:
            self.rows.append(row)
            self._refresh_rows(select_id=row.id)
            self._show_note(f"Added row \u201c{row.name}\u201d.")

    def _edit_row(self) -> None:
        row = self._selected_row()
        if row is None:
            self._show_note("Select a row to edit first.")
            return
        updated = self._row_dialog(row.clone()).show()
        if updated is not None:
            for index, existing in enumerate(self.rows):
                if existing.id == row.id:
                    self.rows[index] = updated
                    break
            self._refresh_rows(select_id=updated.id)
            self._show_note(f"Updated row \u201c{updated.name}\u201d.")

    def _duplicate_row(self) -> None:
        row = self._selected_row()
        if row is None:
            self._show_note("Select a row to duplicate first.")
            return
        clone = row.clone()
        clone.id = new_id("row")
        clone.name = f"{row.name} copy".strip()
        index = self.rows.index(row)
        self.rows.insert(index + 1, clone)
        self._refresh_rows(select_id=clone.id)
        self._show_note("Row duplicated.")

    def _remove_row(self) -> None:
        row = self._selected_row()
        if row is None:
            self._show_note("Select a row to remove first.")
            return
        index = self.rows.index(row)
        self.rows.pop(index)
        next_id = self.rows[min(index, len(self.rows) - 1)].id if self.rows else None
        self._refresh_rows(select_id=next_id)
        self._show_note(f"Removed \u201c{row.name}\u201d. Cancel to undo this edit.")

    def _move_row(self, direction: int) -> None:
        row = self._selected_row()
        if row is None:
            self._show_note("Select a row to reorder first.")
            return
        index = self.rows.index(row)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.rows):
            return
        self.rows[index], self.rows[new_index] = self.rows[new_index], self.rows[index]
        self._refresh_rows(select_id=row.id)

    def _submit(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self._show_note("Please enter a table name.", "error")
            self.name_entry.focus_set()
            return
        for table in self.project.tables:
            if table.id != self._table.id and table.name.strip().lower() == name.lower():
                self._show_note(
                    f"A table named \u201c{table.name}\u201d already exists. Choose another name.",
                    "error",
                )
                self.name_entry.focus_set()
                return
        for row in self.rows:
            if not row.name.strip():
                self._show_note("Every row needs a name.", "error")
                return
            if self._kind == MENU:
                row.type = MENU_ROW
            elif self._kind == COMPONENTS:
                row.type = normalize_component_type(row.type)
            elif not str(row.type).strip() or row.type == MENU_ROW:
                row.type = "Text"
            if row.link_table_id == self._table.id:
                row.link_table_id = None
        self._table.name = name
        self._table.kind = self._kind
        self._table.notes = text_value(self.notes).strip()
        self._table.rows = [row.clone() for row in self.rows]
        self.result = self._table
        self._accept()


class RowDialog(BaseDialog):
    """Add or edit one menu item / field / component row."""

    def __init__(
        self,
        parent,
        *,
        row: Row | None,
        table_kind: str,
        targets: list[Table],
        title: str,
    ):
        self.table_kind = table_kind
        self.targets = targets
        self._row = row.clone() if row else Row(name="", type=row_type_for(table_kind))
        editing = row is not None
        if table_kind == MENU:
            subtitle = "Describe a menu item and optionally point it at another table."
        elif table_kind == COMPONENTS:
            subtitle = "Describe a UI component, its type, and where it is used."
        else:
            subtitle = "Describe a field, its type, and any validation or behavior notes."
        super().__init__(parent, title, subtitle, width=640, height=570)
        self._build()
        self.add_footer_button("Cancel", self._cancel)
        self._primary = self.add_footer_button(
            "Save row" if editing else "Add row",
            self._submit,
            variant="primary",
            weight="bold",
        )
        self.footer_note.configure(
            text="Link to table draws the arrow from this row."
        )
        self.bind("<Control-Return>", lambda _e: self._submit())

    def _build(self) -> None:
        content = tk.Frame(self.body, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=24, pady=(16, 8))

        field_label(content, "Row name").pack(fill="x", pady=(0, 6))
        self.name_var = tk.StringVar(value=self._row.name)
        self.name_entry = make_entry(content, self.name_var)
        self.name_entry.pack(fill="x", ipady=6)
        self.name_entry.bind("<Return>", lambda _e: self._submit())

        two = tk.Frame(content, bg=theme.BG)
        two.pack(fill="x", pady=(14, 0))
        two.grid_columnconfigure(0, weight=1, uniform="col")
        two.grid_columnconfigure(1, weight=1, uniform="col")

        type_frame = tk.Frame(two, bg=theme.BG)
        type_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        field_label(type_frame, "Type").pack(fill="x", pady=(0, 6))
        if self.table_kind == MENU:
            initial_type = MENU_ROW
        elif self.table_kind == COMPONENTS:
            initial_type = normalize_component_type(self._row.type)
        else:
            initial_type = self._row.type or "Text"
        self.type_var = tk.StringVar(value=initial_type)
        if self.table_kind == MENU:
            self.type_widget = make_entry(type_frame, self.type_var)
            self.type_widget.configure(
                state="disabled",
                disabledbackground=theme.MENU_BG,
                disabledforeground=theme.MENU_FG,
                font=theme.font(10, "bold"),
            )
            self.type_widget.pack(fill="x", ipady=6)
        elif self.table_kind == COMPONENTS:
            self.type_widget = ttk.Combobox(
                type_frame,
                textvariable=self.type_var,
                values=list(COMPONENT_TYPES),
                state="readonly",
                font=theme.font(10),
            )
            self.type_widget.pack(fill="x", ipady=4)
        else:
            self.type_widget = ttk.Combobox(
                type_frame,
                textvariable=self.type_var,
                values=list(FIELD_TYPES),
                state="normal",
                font=theme.font(10),
            )
            self.type_widget.pack(fill="x", ipady=4)
        if self.table_kind == MENU:
            type_hint = "All rows in a menu table are Menu items."
        elif self.table_kind == COMPONENTS:
            type_hint = "Button, TextBox, Text Area, Table, Tabs, or H1\u2013H6."
        else:
            type_hint = "Pick a type or type a custom one."
        tk.Label(
            type_frame,
            text=type_hint,
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
            anchor="w",
            justify="left",
            wraplength=260,
        ).pack(fill="x", pady=(5, 0))

        link_frame = tk.Frame(two, bg=theme.BG)
        link_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        field_label(link_frame, "Links to table").pack(fill="x", pady=(0, 6))
        self.link_var = tk.StringVar()
        values = ["None (no link)"]
        self._link_map = {"None (no link)": None}
        for target in self.targets:
            label = f"{target.name}  ({target.kind_short})"
            if label in self._link_map:
                label = f"{label}  [{target.id[-4:]}]"
            values.append(label)
            self._link_map[label] = target.id
        current_label = "None (no link)"
        if self._row.link_table_id:
            for label, target_id in self._link_map.items():
                if target_id == self._row.link_table_id:
                    current_label = label
                    break
        self.link_var.set(current_label)
        self.link_combo = ttk.Combobox(
            link_frame,
            textvariable=self.link_var,
            values=values,
            state="readonly" if self.targets else "disabled",
            font=theme.font(10),
        )
        self.link_combo.pack(fill="x", ipady=4)
        if self.table_kind == MENU:
            link_hint = "The row opens this target table."
        elif self.table_kind == COMPONENTS:
            link_hint = "Optional: component opens this table."
        else:
            link_hint = "Optional foreign-key / detail link."
        tk.Label(
            link_frame,
            text=link_hint,
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
            anchor="w",
        ).pack(fill="x", pady=(5, 0))

        head = tk.Frame(content, bg=theme.BG)
        head.pack(fill="x", pady=(14, 0))
        field_label(head, "Notes").pack(side="left")
        tk.Label(
            head,
            text="optional \u00b7 extra behavior, values, or instructions",
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
        ).pack(side="left", padx=(8, 0))
        self.notes = make_text(content, height=6)
        self.notes.pack(fill="both", expand=True, pady=(6, 0))
        self.notes.insert("1.0", self._row.notes)

    def focus_first(self) -> None:
        self.name_entry.focus_set()

    def _submit(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.footer_note.configure(
                text="Please enter a row name.", fg=theme.DANGER
            )
            self.name_entry.focus_set()
            return
        if self.table_kind == MENU:
            type_name = MENU_ROW
        elif self.table_kind == COMPONENTS:
            type_name = normalize_component_type(self.type_var.get())
        else:
            type_name = self.type_var.get().strip() or "Text"
        link_label = self.link_var.get()
        link_id = self._link_map.get(link_label)
        self._row.name = name
        self._row.type = type_name
        self._row.notes = text_value(self.notes).strip()
        self._row.link_table_id = link_id
        self.result = self._row
        self._accept()


def row_type_for(kind: str) -> str:
    if kind == MENU:
        return MENU_ROW
    if kind == COMPONENTS:
        return "Button"
    return "Text"


class ProjectDialog(BaseDialog):
    """Create a project or edit project-level metadata."""

    def __init__(self, parent, project: Project, *, creating: bool = False):
        self.project = project
        self.creating = creating
        super().__init__(
            parent,
            "New project" if creating else "Project details",
            (
                "Name your project and describe what you want to build. "
                "These details become the opening of the AI brief."
                if creating
                else "The name and description appear at the top of the AI brief."
            ),
            width=660,
            height=500,
        )
        self._build()
        self.add_footer_button("Cancel", self._cancel)
        self.add_footer_button(
            "Create project" if creating else "Save details",
            self._submit,
            variant="primary",
            weight="bold",
        )
        if creating:
            self.footer_note.configure(text="You can change these details later.")
        else:
            self.footer_note.configure(
                text=f"Created {_format_timestamp(project.created_at)}"
            )
        self.bind("<Control-Return>", lambda _e: self._submit())

    def _build(self) -> None:
        content = tk.Frame(self.body, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=24, pady=16)
        field_label(content, "Project name").pack(fill="x", pady=(0, 6))
        self.name_var = tk.StringVar(value=self.project.name)
        self.name_entry = make_entry(content, self.name_var)
        self.name_entry.pack(fill="x", ipady=6)
        self.name_entry.bind("<Return>", lambda _e: self._submit())
        field_label(content, "Description").pack(fill="x", pady=(16, 6))
        self.description = make_text(content, height=7)
        self.description.pack(fill="both", expand=True)
        self.description.insert("1.0", self.project.description)
        tk.Label(
            content,
            text=(
                "Describe what the app should do. The AI will use this alongside "
                "the menu and database tables."
            ),
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
            anchor="w",
            justify="left",
            wraplength=580,
        ).pack(fill="x", pady=(6, 0))

    def focus_first(self) -> None:
        self.name_entry.focus_set()
        if self.creating:
            self.name_entry.selection_range(0, "end")
            self.name_entry.icursor("end")

    def _submit(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.footer_note.configure(text="Please enter a project name.", fg=theme.DANGER)
            self.name_entry.focus_set()
            return
        self.result = {
            "name": name,
            "description": text_value(self.description).strip(),
        }
        self._accept()


class BriefDialog(BaseDialog):
    """Read-only preview of the generated AI prompt."""

    def __init__(self, parent, project: Project, brief: str):
        self.project = project
        self.brief = brief
        super().__init__(
            parent,
            "AI brief",
            "Copy this Markdown into any AI coding tool. It describes the whole diagram.",
            width=1000,
            height=740,
            resizable=True,
        )
        self._build()
        self.add_footer_button("Close", self._accept)
        primary = self.add_footer_button(
            "Copy brief", self._copy, variant="primary", weight="bold"
        )
        self.add_footer_button("Save as .md\u2026", self._save)
        self.footer_note.configure(
            text=f"{len(brief.splitlines())} lines \u00b7 Markdown \u00b7 offline"
        )
        self._copy_button = primary
        self.bind("<Control-s>", lambda _e: self._save())

    def _build(self) -> None:
        content = tk.Frame(self.body, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=22, pady=18)
        meta = tk.Frame(content, bg=theme.BG)
        meta.pack(fill="x", pady=(0, 8))
        tk.Label(
            meta,
            text="MARKDOWN",
            bg=theme.ACCENT_SOFT,
            fg=theme.ACCENT_TEXT,
            font=theme.font(8, "bold"),
            padx=8,
            pady=3,
        ).pack(side="left")
        tk.Label(
            meta,
            text="Source of truth for your build. Edit the diagram and translate again anytime.",
            bg=theme.BG,
            fg=theme.MUTED,
            font=theme.font(8),
        ).pack(side="left", padx=(10, 0))

        wrap = tk.Frame(
            content,
            bg=theme.SURFACE,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
        )
        wrap.pack(fill="both", expand=True)
        self.text = tk.Text(
            wrap,
            wrap="word",
            bg=theme.SURFACE,
            fg=theme.INK_SOFT,
            relief="flat",
            bd=0,
            padx=20,
            pady=16,
            font=theme.font(9, family=theme.MONO_FAMILY),
            spacing1=1,
            spacing3=2,
            cursor="arrow",
        )
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure(
            "h1",
            font=theme.font(13, "bold", family=theme.MONO_FAMILY),
            foreground=theme.ACCENT_TEXT,
            spacing1=10,
            spacing3=6,
        )
        self.text.tag_configure(
            "h2",
            font=theme.font(10, "bold", family=theme.MONO_FAMILY),
            foreground=theme.INK,
            spacing1=8,
            spacing3=4,
        )
        self.text.tag_configure(
            "h3",
            font=theme.font(9, "bold", family=theme.MONO_FAMILY),
            foreground=theme.INK_SOFT,
            spacing1=6,
            spacing3=2,
        )
        self.text.tag_configure("quote", foreground=theme.MUTED)
        self.text.tag_configure("table", foreground="#69758A")
        for line in self.brief.splitlines(keepends=True):
            if line.startswith("# "):
                tag = "h1"
            elif line.startswith("## "):
                tag = "h2"
            elif line.startswith("### "):
                tag = "h3"
            elif line.startswith(">"):
                tag = "quote"
            elif line.startswith("|"):
                tag = "table"
            else:
                tag = ()
            self.text.insert("end", line, tag)
        self.text.configure(state="disabled")

    def focus_first(self) -> None:
        self.text.focus_set()

    def _note(self, text: str, tone: str = "muted") -> None:
        color = {
            "success": theme.SUCCESS,
            "error": theme.DANGER,
        }.get(tone, theme.MUTED)
        self.footer_note.configure(text=text, fg=color)

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.brief)
        self.update_idletasks()
        self._note("Copied the AI brief to the clipboard.", "success")

    def _save(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save AI brief",
            defaultextension=".md",
            initialfile=default_brief_filename(self.project),
            filetypes=[
                ("Markdown", "*.md"),
                ("Text file", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            Path(path).write_text(self.brief, encoding="utf-8")
        except OSError as exc:
            self._note(f"Could not save: {exc}", "error")
            return
        self._note(f"Saved to {path}", "success")
