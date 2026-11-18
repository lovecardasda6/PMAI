"""Headless-ish UI workflow tests.

The dialogs themselves are replaced with small fakes so these tests exercise
the command wiring (undo, dirty state, persistence, linking and dragging)
without blocking on a real modal window.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pmai import cardmetrics
from pmai.models import MENU, Row, Table
from pmai.ui import main as main_module
from pmai.ui.diagram import Hit
from pmai.ui.main import MainWindow


def table_named(app: MainWindow, name: str) -> Table:
    return next(table for table in app.project.tables if table.name == name)


class FakeNewProjectDialog:
    """Stand-in for the new-project metadata prompt."""

    name = "Untitled Project"
    description = ""

    def __init__(self, parent, project, *, creating=False):
        self.project = project
        self.creating = creating

    def show(self):
        return {"name": self.name, "description": self.description}


def test_sample_project_loads(app: MainWindow):
    assert app.project.name == "Billing Demo"
    assert len(app.project.tables) == 4
    assert len(app.project.menu_tables()) == 2
    assert len(app.project.field_tables()) == 2
    assert app.project.total_rows() == 15
    assert app.dirty is True
    assert "4 tables" in app.counts_label.cget("text")
    assert app.view.link_mode is False


def test_add_table_from_dialog_and_undo(app: MainWindow, monkeypatch):
    class FakeTableDialog:
        def __init__(self, parent, project, table=None):
            self.project = project

        def show(self):
            invoice = next(
                t for t in self.project.tables if t.name == "Invoice"
            )
            return Table(
                name="Reports",
                kind=MENU,
                notes="Reporting section.",
                rows=[
                    Row(name="Overview"),
                    Row(name="Invoices", link_table_id=invoice.id),
                ],
            )

    monkeypatch.setattr(main_module, "TableDialog", FakeTableDialog)
    app.add_table()

    reports = table_named(app, "Reports")
    assert len(app.project.tables) == 5
    assert app.view.selected_table_id == reports.id
    assert reports.rows[1].link_table_id == table_named(app, "Invoice").id
    assert app._undo[-1][0] == "Add table"
    assert app.dirty is True

    app.undo()
    assert len(app.project.tables) == 4
    assert app.project.get_table(reports.id) is None

    app.redo()
    assert len(app.project.tables) == 5
    assert table_named(app, "Reports") is not None


def test_edit_table_from_dialog_keeps_position(app: MainWindow, monkeypatch):
    invoice = table_named(app, "Invoice")
    original = invoice.clone()

    class FakeTableDialog:
        def __init__(self, parent, project, table=None):
            self.table = table

        def show(self):
            result = self.table.clone()
            result.name = "Invoices"
            result.notes = "Renamed in the test."
            return result

    monkeypatch.setattr(main_module, "TableDialog", FakeTableDialog)
    app.edit_table(invoice.id)

    renamed = table_named(app, "Invoices")
    assert renamed.id == invoice.id
    assert renamed.notes == "Renamed in the test."
    assert renamed.x == pytest.approx(original.x)
    assert renamed.y == pytest.approx(original.y)
    assert app.dirty is True

    app.undo()
    assert table_named(app, "Invoice") is not None


def test_edit_row_from_dialog(app: MainWindow, monkeypatch):
    billing = table_named(app, "Billing")
    row = billing.rows[0]

    class FakeRowDialog:
        def __init__(self, parent, **kwargs):
            self.row = kwargs["row"]

        def show(self):
            result = self.row.clone()
            result.name = "Subscription"
            return result

    monkeypatch.setattr(main_module, "RowDialog", FakeRowDialog)
    app.edit_row(billing.id, row.id)

    assert billing.rows[0].name == "Subscription"
    assert billing.rows[0].type == "Menu"
    assert app.view.selected_row_id == row.id
    app.undo()
    assert table_named(app, "Billing").rows[0].name == "Invoice"


def test_project_details_dialog(app: MainWindow, monkeypatch):
    class FakeProjectDialog:
        def __init__(self, parent, project):
            pass

        def show(self):
            return {"name": "Billing Suite", "description": "A bigger app."}

    monkeypatch.setattr(main_module, "ProjectDialog", FakeProjectDialog)
    app.edit_project_details()

    assert app.project.name == "Billing Suite"
    assert app.project.description == "A bigger app."
    assert app.name_var.get() == "Billing Suite"
    app.undo()
    assert app.project.name == "Billing Demo"


def test_link_mode_click_sequence(app: MainWindow):
    sidebar = table_named(app, "Sidebar")
    dashboard = sidebar.rows[0]
    transactions = table_named(app, "Transactions")
    assert dashboard.link_table_id is None

    app.view.set_link_mode(True)
    assert app.view.link_mode is True
    assert "Linking" in app.link_btn.cget("text")

    app.view._handle_link_click(Hit("row", sidebar, dashboard))
    assert app.view.link_source == (sidebar.id, dashboard.id)
    app.view._handle_link_click(Hit("header", transactions))

    assert dashboard.link_table_id == transactions.id
    assert app.view.link_source is None
    assert app._undo[-1][0] == "Change link"

    app.undo()
    # Undo replaces the project, so re-read the row.
    assert table_named(app, "Sidebar").rows[0].link_table_id is None
    app.view.set_link_mode(False)


def test_drag_from_row_area_moves_table(app: MainWindow):
    view = app.view
    view.zoom = 1.0
    view.pan_x = 0.0
    view.pan_y = 0.0
    table = table_named(app, "Sidebar")
    start_x = table.x + 100
    start_y = (
        table.y
        + cardmetrics.HEADER_H
        + cardmetrics.COL_H
        + cardmetrics.ROW_H / 2
    )
    original_x, original_y = table.x, table.y

    class Event:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    view._on_left_press(Event(start_x, start_y))
    assert view._drag is not None
    view._on_left_drag(Event(start_x + 90, start_y + 50))
    view._on_left_release(Event(start_x + 90, start_y + 50))

    moved = table_named(app, "Sidebar")
    assert moved.x == pytest.approx(original_x + 90)
    assert moved.y == pytest.approx(original_y + 50)
    assert app._undo[-1][0] == "Move table"
    assert app.dirty is True

    app.undo()
    restored = table_named(app, "Sidebar")
    assert restored.x == pytest.approx(original_x)
    assert restored.y == pytest.approx(original_y)


def test_delete_table_clears_links_and_undo(app: MainWindow, monkeypatch):
    invoice = table_named(app, "Invoice")
    billing = table_named(app, "Billing")
    assert billing.rows[0].link_table_id == invoice.id

    monkeypatch.setattr(
        main_module.messagebox, "askyesno", lambda *args, **kwargs: True
    )
    app.delete_table(invoice.id)

    assert app.project.get_table(invoice.id) is None
    assert len(app.project.tables) == 3
    assert table_named(app, "Billing").rows[0].link_table_id is None
    assert app._undo[-1][0] == "Delete table"

    app.undo()
    assert len(app.project.tables) == 4
    assert table_named(app, "Billing").rows[0].link_table_id == invoice.id


def test_save_and_open_through_ui(app: MainWindow, monkeypatch, tmp_path: Path):
    target = tmp_path / "ui-save.pmproj"
    monkeypatch.setattr(
        main_module.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )
    assert app.save_project_as() is True
    assert target.exists()
    assert app.file_path == target
    assert app.dirty is False

    app.project.description = "Changed before reopening."
    app.mark_dirty()
    monkeypatch.setattr(
        main_module.messagebox, "askyesnocancel", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(main_module, "ProjectDialog", FakeNewProjectDialog)
    app.new_project()
    assert app.project.tables == []
    assert app.project.name == "Untitled Project"

    monkeypatch.setattr(
        main_module.filedialog,
        "askopenfilename",
        lambda **kwargs: str(target),
    )
    app.open_project()
    assert app.project.name == "Billing Demo"
    assert len(app.project.tables) == 4
    assert app.file_path == target
    assert app.dirty is False


def test_export_brief_through_ui(app: MainWindow, monkeypatch, tmp_path: Path):
    target = tmp_path / "brief.md"
    monkeypatch.setattr(
        main_module.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )
    app.export_brief()
    text = target.read_text(encoding="utf-8")
    assert "AI Build Brief" in text
    assert "Billing Demo" in text
    assert "Invoice #" in text


def test_show_brief_passes_markdown_to_dialog(app: MainWindow, monkeypatch):
    captured = {}

    class FakeBriefDialog:
        def __init__(self, parent, project, brief):
            captured["project"] = project
            captured["brief"] = brief

        def show(self):
            return None

    monkeypatch.setattr(main_module, "BriefDialog", FakeBriefDialog)
    app.show_brief()

    assert captured["project"] is app.project
    assert "## 3. Menu tables (navigation)" in captured["brief"]
    assert "## 4. Modal / database-field tables" in captured["brief"]


def test_empty_state_after_new_project(app: MainWindow, monkeypatch):
    monkeypatch.setattr(
        main_module.messagebox, "askyesnocancel", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(main_module, "ProjectDialog", FakeNewProjectDialog)
    app.new_project()

    assert app.project.tables == []
    assert app.file_path is None
    assert app.dirty is False
    assert app.view.empty.winfo_manager() == "place"
    assert "0 tables" in app.counts_label.cget("text")


def test_new_project_prompts_for_description(app: MainWindow, monkeypatch):
    captured = {}

    class FakeProjectDialog:
        def __init__(self, parent, project, *, creating=False):
            captured["name"] = project.name
            captured["creating"] = creating

        def show(self):
            return {
                "name": "Inventory",
                "description": "Track stock, suppliers, and reorder points.",
            }

    monkeypatch.setattr(main_module, "ProjectDialog", FakeProjectDialog)
    monkeypatch.setattr(
        main_module.messagebox, "askyesnocancel", lambda *args, **kwargs: False
    )

    app.new_project()

    assert captured == {"name": "Untitled Project", "creating": True}
    assert app.project.name == "Inventory"
    assert app.project.description == "Track stock, suppliers, and reorder points."
    assert app.project.tables == []
    assert app.file_path is None
    assert app.name_var.get() == "Inventory"


def test_cancelling_new_project_keeps_the_current_project(app: MainWindow, monkeypatch):
    class CancelledProjectDialog:
        def __init__(self, parent, project, *, creating=False):
            pass

        def show(self):
            return None

    monkeypatch.setattr(main_module, "ProjectDialog", CancelledProjectDialog)
    monkeypatch.setattr(
        main_module.messagebox, "askyesnocancel", lambda *args, **kwargs: False
    )

    app.new_project()

    assert app.project.name == "Billing Demo"
    assert len(app.project.tables) == 4
