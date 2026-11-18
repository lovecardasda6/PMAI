"""A ready-made demo project based on the sidebar / billing example."""

from __future__ import annotations

from .layout import auto_layout
from .models import Project, Row, Table, new_id


def _row(name: str, type_: str = "Menu", notes: str = "", link: str | None = None) -> Row:
    return Row(id=new_id("row"), name=name, type=type_, notes=notes, link_table_id=link)


def build_sample_project() -> Project:
    sidebar = Table(
        id=new_id("tbl"),
        name="Sidebar",
        kind="menu",
        notes="I want this table to appear in the sidebar.",
        rows=[
            _row("Dashboard"),
            _row("Billing"),
        ],
    )
    billing = Table(
        id=new_id("tbl"),
        name="Billing",
        kind="menu",
        notes=(
            "This is a sub-menu of Sidebar > Billing. Keep it inside the "
            "sidebar navigation."
        ),
        rows=[
            _row("Invoice"),
            _row("Transactions"),
        ],
    )
    invoice = Table(
        id=new_id("tbl"),
        name="Invoice",
        kind="fields",
        notes="Auto-generate the invoice number if it is left blank.",
        rows=[
            _row("Invoice #", "Text", "Auto-generated when blank."),
            _row("Date/Time", "DateTime"),
            _row("Customer", "Text"),
            _row("Amount", "Currency"),
            _row("Status", "Select", "Draft, Sent, Paid, Void"),
            _row("Notes", "Long Text"),
        ],
    )
    transactions = Table(
        id=new_id("tbl"),
        name="Transactions",
        kind="fields",
        notes="Show newest transactions first.",
        rows=[
            _row("Date/Time", "DateTime"),
            _row("Type", "Select", "Income or Expense"),
            _row("Amount", "Currency"),
            _row("Reference", "Text"),
            _row("Notes", "Long Text"),
        ],
    )

    sidebar.rows[1].link_table_id = billing.id
    billing.rows[0].link_table_id = invoice.id
    billing.rows[1].link_table_id = transactions.id

    project = Project(
        name="Billing Demo",
        description=(
            "A small billing app with a sidebar navigation, invoices, and a "
            "transaction log."
        ),
        tables=[sidebar, billing, invoice, transactions],
    )
    auto_layout(project)
    project.normalize()
    return project
