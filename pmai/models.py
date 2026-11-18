"""Core data model for PMAI projects.

A project is a collection of tables.  Menu tables describe navigation, field
tables describe modal / database models, and component tables describe reusable
UI pieces (buttons, tables, and headings).  Rows may optionally point to
another table, which is what the diagram arrows represent.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MENU = "menu"
FIELDS = "fields"
COMPONENTS = "components"
TABLE_KINDS = (MENU, FIELDS, COMPONENTS)

MENU_ROW = "Menu"

COMPONENT_TYPES: tuple[str, ...] = (
    "Button",
    "TextBox",
    "Text Area",
    "Table",
    "Tabs",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
)

_COMPONENT_TYPE_LOOKUP = {value.lower(): value for value in COMPONENT_TYPES}
_COMPONENT_TYPE_ALIASES = {
    "text box": "TextBox",
    "text-box": "TextBox",
    "textbox input": "TextBox",
    "input": "TextBox",
    "text area": "Text Area",
    "textarea": "Text Area",
    "text-area": "Text Area",
    "multiline": "Text Area",
    "multi-line": "Text Area",
    "multiline text": "Text Area",
    "heading 1": "H1",
    "heading 2": "H2",
    "heading 3": "H3",
    "heading 4": "H4",
    "heading 5": "H5",
    "heading 6": "H6",
    "h1 heading": "H1",
    "h2 heading": "H2",
    "h3 heading": "H3",
    "h4 heading": "H4",
    "h5 heading": "H5",
    "h6 heading": "H6",
    "grid": "Table",
    "datatable": "Table",
    "data table": "Table",
    "tab": "Tabs",
    "tab bar": "Tabs",
    "tab group": "Tabs",
    "tab set": "Tabs",
    "tabbed view": "Tabs",
}

FIELD_TYPES: tuple[str, ...] = (
    "Text",
    "Long Text",
    "Number",
    "Integer",
    "Decimal",
    "Currency",
    "Boolean",
    "Date",
    "Time",
    "DateTime",
    "Email",
    "Phone",
    "URL",
    "Select",
    "Multi Select",
    "Auto ID",
    "Reference",
    "File",
    "Image",
    "Password",
    "JSON",
    "Formula",
)

KIND_SHORT_LABELS = {
    MENU: "menu",
    FIELDS: "modal/fields",
    COMPONENTS: "components",
}

SCHEMA_NAME = "PMAI"
SCHEMA_VERSION = 2


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


MAX_COORDINATE = 1_000_000.0


def safe_coordinate(value: Any, default: float = 60.0) -> float:
    """Return a finite, reasonably bounded canvas coordinate."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(-MAX_COORDINATE, min(MAX_COORDINATE, number))


def normalize_kind(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {MENU, "nav", "navigation", "sidebar"}:
        return MENU
    if text in {COMPONENTS, "component", "ui", "ui components", "ui-components"}:
        return COMPONENTS
    return FIELDS


def is_component_type(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in _COMPONENT_TYPE_LOOKUP or text in _COMPONENT_TYPE_ALIASES


def normalize_component_type(value: Any, default: str = "Button") -> str:
    """Return a canonical component type, tolerating case and heading aliases."""
    text = str(value or "").strip().lower()
    if text in _COMPONENT_TYPE_LOOKUP:
        return _COMPONENT_TYPE_LOOKUP[text]
    if text in _COMPONENT_TYPE_ALIASES:
        return _COMPONENT_TYPE_ALIASES[text]
    return default


@dataclass
class Row:
    """One row of a table: a menu item, database field, or UI component."""

    id: str = field(default_factory=lambda: new_id("row"))
    name: str = ""
    type: str = MENU_ROW
    notes: str = ""
    link_table_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "notes": self.notes,
            "link_table_id": self.link_table_id,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Row | None":
        if not isinstance(data, dict):
            return None
        link = data.get("link_table_id")
        return cls(
            id=str(data.get("id") or new_id("row")),
            name=str(data.get("name") or ""),
            type=str(data.get("type") or MENU_ROW),
            notes=str(data.get("notes") or ""),
            link_table_id=str(link) if link else None,
        )

    def clone(self) -> "Row":
        return Row(
            id=self.id,
            name=self.name,
            type=self.type,
            notes=self.notes,
            link_table_id=self.link_table_id,
        )


@dataclass
class Table:
    """A menu table, a modal/database-field table, or a component table."""

    id: str = field(default_factory=lambda: new_id("tbl"))
    name: str = "Untitled table"
    kind: str = MENU
    notes: str = ""
    x: float = 60.0
    y: float = 60.0
    rows: list[Row] = field(default_factory=list)

    @property
    def kind_short(self) -> str:
        return KIND_SHORT_LABELS.get(self.kind, "modal/fields")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "notes": self.notes,
            "x": round(float(self.x), 2),
            "y": round(float(self.y), 2),
            "rows": [row.to_dict() for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Table | None":
        if not isinstance(data, dict):
            return None
        rows: list[Row] = []
        raw_rows = data.get("rows")
        if isinstance(raw_rows, list):
            for raw in raw_rows:
                row = Row.from_dict(raw)
                if row is not None:
                    rows.append(row)
        x = safe_coordinate(data.get("x", 60))
        y = safe_coordinate(data.get("y", 60))
        return cls(
            id=str(data.get("id") or new_id("tbl")),
            name=str(data.get("name") or "Untitled table"),
            kind=normalize_kind(data.get("kind")),
            notes=str(data.get("notes") or ""),
            x=x,
            y=y,
            rows=rows,
        )

    def clone(self, *, new_ids: bool = False) -> "Table":
        clone = Table.from_dict(self.to_dict())
        assert clone is not None
        if new_ids:
            clone.id = new_id("tbl")
            for row in clone.rows:
                row.id = new_id("row")
        return clone


@dataclass
class Project:
    """The whole project document."""

    name: str = "Untitled Project"
    description: str = ""
    tables: list[Table] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    # ---- lookup helpers -------------------------------------------------

    def get_table(self, table_id: str | None) -> Table | None:
        if not table_id:
            return None
        for table in self.tables:
            if table.id == table_id:
                return table
        return None

    def get_row(self, table_id: str, row_id: str) -> Row | None:
        table = self.get_table(table_id)
        if not table:
            return None
        for row in table.rows:
            if row.id == row_id:
                return row
        return None

    def menu_tables(self) -> list[Table]:
        return [t for t in self.tables if t.kind == MENU]

    def field_tables(self) -> list[Table]:
        return [t for t in self.tables if t.kind == FIELDS]

    def component_tables(self) -> list[Table]:
        return [t for t in self.tables if t.kind == COMPONENTS]

    def total_rows(self) -> int:
        return sum(len(t.rows) for t in self.tables)

    def incoming_links(self) -> dict[str, list[tuple[Table, Row]]]:
        incoming: dict[str, list[tuple[Table, Row]]] = {
            t.id: [] for t in self.tables
        }
        ids = set(incoming)
        for table in self.tables:
            for row in table.rows:
                if row.link_table_id in ids and row.link_table_id != table.id:
                    incoming[row.link_table_id].append((table, row))
        return incoming

    def root_menu_tables(self) -> list[Table]:
        incoming = self.incoming_links()
        roots = [t for t in self.menu_tables() if not incoming.get(t.id)]
        return roots

    # ---- mutation helpers ----------------------------------------------

    def add_table(self, table: Table) -> Table:
        self.tables.append(table)
        return table

    def remove_table(self, table_id: str) -> Table | None:
        removed = None
        for table in list(self.tables):
            if table.id == table_id:
                removed = table
                self.tables.remove(table)
            for row in table.rows:
                if row.link_table_id == table_id:
                    row.link_table_id = None
        return removed

    def unique_table_name(self, base: str, *, exclude_id: str | None = None) -> str:
        existing = {
            t.name.strip().lower()
            for t in self.tables
            if t.id != exclude_id
        }
        base = base.strip() or "Untitled table"
        if base.lower() not in existing:
            return base
        index = 2
        while f"{base} {index}".lower() in existing:
            index += 1
        return f"{base} {index}"

    def normalize(self) -> None:
        """Repair imported / hand-edited data and dangling links."""
        table_ids: set[str] = set()
        row_ids: set[str] = set()
        for table in self.tables:
            if not table.id or table.id in table_ids:
                table.id = new_id("tbl")
            table_ids.add(table.id)
            if table.kind not in TABLE_KINDS:
                table.kind = FIELDS
            if not str(table.name).strip():
                table.name = "Untitled table"
            table.x = safe_coordinate(table.x)
            table.y = safe_coordinate(table.y)
            for row in table.rows:
                if not row.id or row.id in row_ids:
                    row.id = new_id("row")
                row_ids.add(row.id)
                if not str(row.name).strip():
                    row.name = "Unnamed"
                if table.kind == MENU:
                    row.type = MENU_ROW
                elif table.kind == COMPONENTS:
                    row.type = normalize_component_type(row.type)
                elif not str(row.type).strip():
                    row.type = "Text"

        valid_ids = {t.id for t in self.tables}
        for table in self.tables:
            for row in table.rows:
                if row.link_table_id not in valid_ids or row.link_table_id == table.id:
                    row.link_table_id = None

        if not str(self.name).strip():
            self.name = "Untitled Project"
        self.tables = list(self.tables)

    # ---- serialization -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tables": [table.to_dict() for table in self.tables],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Project":
        if not isinstance(data, dict):
            raise ValueError("Project data must be a JSON object.")

        fmt = data.get("format")
        if fmt is not None and str(fmt).upper() != SCHEMA_NAME:
            raise ValueError("This file is not a PMAI project.")
        try:
            version = int(data.get("version", SCHEMA_VERSION))
        except (TypeError, ValueError):
            version = SCHEMA_VERSION
        if version > SCHEMA_VERSION:
            raise ValueError(
                "This project was created with a newer version of PMAI "
                f"(format {version}, supported {SCHEMA_VERSION})."
            )

        tables: list[Table] = []
        raw_tables = data.get("tables")
        if isinstance(raw_tables, list):
            for raw in raw_tables:
                table = Table.from_dict(raw)
                if table is not None:
                    tables.append(table)

        project = cls(
            name=str(data.get("name") or "Untitled Project"),
            description=str(data.get("description") or ""),
            tables=tables,
            created_at=str(data.get("created_at") or utc_now()),
            updated_at=str(data.get("updated_at") or utc_now()),
        )
        project.normalize()
        return project

    def clone(self) -> "Project":
        return Project.from_dict(self.to_dict())
