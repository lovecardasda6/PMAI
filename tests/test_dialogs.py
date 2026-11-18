"""Tests for the real dialog widgets, without entering modal loops."""

from __future__ import annotations

from pathlib import Path

from pmai.models import FIELDS, MENU, Project, Row, Table
from pmai.ui import dialogs as dialogs_module
from pmai.ui.dialogs import BriefDialog, ProjectDialog, RowDialog, TableDialog


def test_table_dialog_creates_menu_table(root):
    project = Project(name="Test")
    dialog = TableDialog(root, project)
    dialog.name_var.set("Navigation")
    dialog.notes.insert("1.0", "Use a sidebar.")
    dialog.rows = [Row(name="Home"), Row(name="Settings")]

    dialog._submit()

    result = dialog.result
    assert result is not None
    assert result.name == "Navigation"
    assert result.kind == MENU
    assert [row.type for row in result.rows] == ["Menu", "Menu"]
    assert result.notes == "Use a sidebar."


def test_table_dialog_rejects_duplicate_name(root):
    project = Project(tables=[Table(name="Invoice")])
    dialog = TableDialog(root, project)
    dialog.name_var.set("invoice")

    dialog._submit()

    assert dialog.result is None
    assert "already exists" in dialog.footer_note.cget("text")
    dialog._cancel()


def test_table_dialog_requires_a_name(root):
    dialog = TableDialog(root, Project())
    dialog.name_var.set("   ")

    dialog._submit()

    assert dialog.result is None
    assert "table name" in dialog.footer_note.cget("text")
    dialog._cancel()


def test_table_dialog_switch_to_fields_rewrites_menu_rows(root, monkeypatch):
    monkeypatch.setattr(
        dialogs_module.messagebox, "askyesno", lambda *args, **kwargs: True
    )
    table = Table(name="Data", kind=MENU, rows=[Row(name="Home")])
    dialog = TableDialog(root, Project(), table=table)

    dialog._set_kind(FIELDS)
    dialog._submit()

    result = dialog.result
    assert result is not None
    assert result.kind == FIELDS
    assert result.rows[0].type == "Text"


def test_row_dialog_requires_a_name(root):
    dialog = RowDialog(
        root, row=None, table_kind=MENU, targets=[], title="Add row"
    )
    dialog.name_var.set("")

    dialog._submit()

    assert dialog.result is None
    assert "row name" in dialog.footer_note.cget("text")
    dialog._cancel()


def test_row_dialog_menu_item_and_link(root):
    billing = Table(name="Billing", kind=MENU)
    dialog = RowDialog(
        root, row=None, table_kind=MENU, targets=[billing], title="Add row"
    )
    dialog.name_var.set("Billing")
    label = next(
        label for label, table_id in dialog._link_map.items() if table_id == billing.id
    )
    dialog.link_var.set(label)

    dialog._submit()

    result = dialog.result
    assert result is not None
    assert result.name == "Billing"
    assert result.type == "Menu"
    assert result.link_table_id == billing.id


def test_row_dialog_accepts_custom_field_type(root):
    dialog = RowDialog(
        root, row=None, table_kind=FIELDS, targets=[], title="Add row"
    )
    dialog.name_var.set("Rating")
    dialog.type_var.set("Rating (1-5)")
    dialog.notes.insert("1.0", "Required.")

    dialog._submit()

    result = dialog.result
    assert result is not None
    assert result.type == "Rating (1-5)"
    assert result.notes == "Required."


def test_row_dialog_preserves_row_id_when_editing(root):
    row = Row(name="Amount", type="Currency")
    dialog = RowDialog(
        root, row=row, table_kind=FIELDS, targets=[], title="Edit row"
    )
    dialog.name_var.set("Total")

    dialog._submit()

    assert dialog.result is not None
    assert dialog.result.id == row.id
    assert dialog.result.name == "Total"


def test_project_dialog_creation_mode(root):
    dialog = ProjectDialog(root, Project(), creating=True)

    assert dialog._title_label.cget("text") == "New project"
    assert "later" in dialog.footer_note.cget("text")
    dialog.focus_first()
    assert dialog.name_entry.selection_present()


def test_project_dialog_submits_metadata(root):
    project = Project(name="Old Name", description="Old description")
    dialog = ProjectDialog(root, project)
    assert "Created" in dialog.footer_note.cget("text")

    dialog.name_var.set("New Name")
    dialog.description.delete("1.0", "end")
    dialog.description.insert("1.0", "New description")

    dialog._submit()

    assert dialog.result == {
        "name": "New Name",
        "description": "New description",
    }


def test_brief_dialog_copies_and_saves(root, monkeypatch, tmp_path: Path):
    brief = "# AI Build Brief\n\nHello.\n"
    dialog = BriefDialog(root, Project(name="Demo"), brief)

    dialog._copy()
    assert root.clipboard_get() == brief

    target = tmp_path / "brief.md"
    monkeypatch.setattr(
        dialogs_module.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )
    dialog._save()

    assert target.read_text(encoding="utf-8") == brief
    assert "Saved" in dialog.footer_note.cget("text")
    dialog._cancel()
