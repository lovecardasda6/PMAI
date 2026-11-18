from __future__ import annotations

import json
from pathlib import Path

import pytest

from pmai.layout import auto_layout
from pmai.models import (
    COMPONENTS,
    FIELD_TYPES,
    Project,
    Row,
    Table,
    normalize_component_type,
    normalize_kind,
)
from pmai.sample import build_sample_project
from pmai.storage import (
    BIN_MAGIC,
    ProjectFileError,
    decode_project,
    encode_project,
    load_project,
    save_project,
)
from pmai.translation import build_ai_brief, default_brief_filename


def test_project_roundtrip_json(tmp_path: Path):
    project = build_sample_project()
    path = save_project(project, tmp_path / "demo.pmproj")
    loaded = load_project(path)
    assert loaded.name == project.name
    assert len(loaded.tables) == len(project.tables)
    assert loaded.total_rows() == project.total_rows()
    assert loaded.to_dict() == project.to_dict()


def test_project_roundtrip_bin(tmp_path: Path):
    project = build_sample_project()
    path = save_project(project, tmp_path / "demo.bin")
    assert path.read_bytes().startswith(b"PMAI-BIN")
    loaded = load_project(path)
    assert loaded.to_dict() == project.to_dict()


def test_decode_plain_json_without_magic():
    project = build_sample_project()
    loaded = decode_project(encode_project(project, binary=False))
    assert loaded.name == "Billing Demo"


def test_normalize_clears_bad_links():
    a = Table(name="A", kind="menu")
    b = Table(name="B", kind="menu")
    a.rows.append(Row(name="self", type="Menu", link_table_id=a.id))
    a.rows.append(Row(name="valid", type="Menu", link_table_id=b.id))
    a.rows.append(Row(name="missing", type="Menu", link_table_id="nope"))
    project = Project(name="Test", tables=[a, b])
    project.normalize()
    assert a.rows[0].link_table_id is None
    assert a.rows[1].link_table_id == b.id
    assert a.rows[2].link_table_id is None


def test_menu_rows_are_forced_to_menu_type():
    table = Table(
        name="Nav",
        kind="menu",
        rows=[Row(name="Home", type="Text")],
    )
    project = Project(tables=[table])
    project.normalize()
    assert table.rows[0].type == "Menu"


def test_field_types_include_enum_and_dropdown():
    assert "Enum" in FIELD_TYPES
    assert "DropDown" in FIELD_TYPES


def test_component_kind_and_types_are_normalized():
    table = Table(
        name="Invoice UI",
        kind=COMPONENTS,
        rows=[
            Row(name="Save", type="button"),
            Row(name="Email", type="textbox"),
            Row(name="Message", type="textarea"),
            Row(name="Results", type="data table"),
            Row(name="Settings", type="tab group"),
            Row(name="Title", type="heading 1"),
            Row(name="Subtitle", type="h3"),
            Row(name="Mystery", type="something-else"),
        ],
    )
    project = Project(tables=[table])
    project.normalize()

    assert table.kind == COMPONENTS
    assert [row.type for row in table.rows] == [
        "Button",
        "TextBox",
        "Text Area",
        "Table",
        "Tabs",
        "H1",
        "H3",
        "Button",
    ]
    assert project.component_tables() == [table]
    assert normalize_kind("ui components") == COMPONENTS
    assert normalize_component_type("HEADING 6") == "H6"
    assert normalize_component_type("text box") == "TextBox"
    assert normalize_component_type("multi-line") == "Text Area"
    assert normalize_component_type("tab bar") == "Tabs"
    assert normalize_component_type("") == "Button"


def test_remove_table_clears_incoming_links():
    a = Table(name="A", kind="menu")
    b = Table(name="B", kind="fields")
    a.rows.append(Row(name="B", type="Menu", link_table_id=b.id))
    project = Project(tables=[a, b])
    project.remove_table(b.id)
    assert a.rows[0].link_table_id is None


def test_unique_table_name():
    project = Project(tables=[Table(name="Invoice"), Table(name="Invoice 2")])
    assert project.unique_table_name("Invoice") == "Invoice 3"
    assert project.unique_table_name("Invoice", exclude_id=project.tables[0].id) == "Invoice"


def test_auto_layout_places_targets_to_the_right():
    project = build_sample_project()
    auto_layout(project)
    sidebar = next(t for t in project.tables if t.name == "Sidebar")
    billing = next(t for t in project.tables if t.name == "Billing")
    invoice = next(t for t in project.tables if t.name == "Invoice")
    assert sidebar.x < billing.x < invoice.x


def test_brief_contains_tables_links_and_notes():
    brief = build_ai_brief(build_sample_project())
    assert "Billing Demo" in brief
    assert "## 3. Menu tables (navigation)" in brief
    assert "Sidebar" in brief
    assert "Invoice #" in brief
    assert "Auto-generate the invoice number" in brief
    assert "Source table" in brief
    assert "Modal / database-field tables" in brief
    assert "Do **not** invent menu items" in brief


def test_brief_contains_component_tables():
    components = Table(
        name="Invoice UI",
        kind=COMPONENTS,
        notes="Shared across billing screens.",
        rows=[
            Row(name="New invoice", type="Button", notes="Primary action."),
            Row(name="Customer name", type="TextBox"),
            Row(name="Notes", type="Text Area"),
            Row(name="Invoices", type="Table"),
            Row(name="Settings", type="Tabs"),
            Row(name="Billing", type="H1"),
            Row(name="Summary", type="H2"),
        ],
    )
    brief = build_ai_brief(
        Project(name="Components Demo", tables=[components])
    )

    assert "## 5. Component tables (UI building blocks)" in brief
    assert "| Component | Type | Notes | Links to |" in brief
    assert "New invoice" in brief
    assert "| Customer name | TextBox |" in brief
    assert "| Notes | Text Area |" in brief
    assert "| Settings | Tabs |" in brief
    assert "| Billing | H1 |" in brief
    assert "## 6. Link map (drawing arrows)" in brief
    assert "Build the **Invoice UI** component table" in brief
    assert "**Component tables:** 1" in brief


def test_brief_empty_project():
    brief = build_ai_brief(Project())
    assert "does not contain any tables" in brief


def test_brief_escapes_table_pipes_and_newlines():
    table = Table(name="Safety")
    table.rows.append(
        Row(name="Mode", type="Text", notes="left | right\nsecond line")
    )
    brief = build_ai_brief(Project(tables=[table]))
    assert "left \\| right<br>second line" in brief


def test_default_brief_filename():
    assert default_brief_filename(Project(name="Billing Demo")) == (
        "Billing Demo-ai-brief.md"
    )
    assert default_brief_filename(Project(name="  ")) == "project-ai-brief.md"


def test_save_adds_default_extension(tmp_path: Path):
    path = save_project(Project(name="No Extension"), tmp_path / "my-project")
    assert path.name == "my-project.pmproj"
    assert path.exists()


def test_load_missing_file_reports_error(tmp_path: Path):
    with pytest.raises(ProjectFileError, match="Could not open"):
        load_project(tmp_path / "missing.pmproj")


def test_corrupt_file_reports_error(tmp_path: Path):
    path = tmp_path / "broken.pmproj"
    path.write_text("this is not json", encoding="utf-8")
    with pytest.raises(ProjectFileError, match="not valid JSON"):
        load_project(path)


def test_corrupt_binary_file_reports_error():
    with pytest.raises(ProjectFileError, match="corrupted"):
        decode_project(BIN_MAGIC + b"not gzip data")


def test_non_finite_and_huge_coordinates_are_repaired():
    table = Table(name="A", x=float("nan"), y=float("inf"))
    Project(tables=[table]).normalize()
    assert table.x == 60.0
    assert table.y == 60.0

    huge = Table(name="B", x=1e12, y=-1e12)
    Project(tables=[huge]).normalize()
    assert huge.x == 1_000_000.0
    assert huge.y == -1_000_000.0


def test_newer_schema_is_rejected():
    data = Project(name="Future").to_dict()
    data["version"] = 99
    with pytest.raises(ProjectFileError, match="newer version"):
        decode_project(json.dumps(data).encode("utf-8"))


def test_auto_layout_handles_link_cycle():
    a = Table(name="A", kind="menu")
    b = Table(name="B", kind="menu")
    a.rows.append(Row(name="to B", type="Menu", link_table_id=b.id))
    b.rows.append(Row(name="to A", type="Menu", link_table_id=a.id))
    project = Project(tables=[a, b])

    auto_layout(project)

    # The back edge is broken by the stack guard, so both tables still get
    # placed in distinct columns instead of recursing forever.
    assert a.x != b.x
    assert a.x >= 60 and b.x >= 60
    assert a.y >= 60 and b.y >= 60


def test_bundled_sample_project_loads():
    path = (
        Path(__file__).resolve().parent.parent
        / "samples"
        / "billing-demo.pmproj"
    )
    assert path.exists()
    project = load_project(path)
    assert project.name == "Billing Demo"
    assert len(project.tables) == 4
    assert project.total_rows() == 15
