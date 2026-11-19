"""Main application window and command wiring."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import APP_NAME, APP_TAGLINE, __version__
from ..layout import auto_layout
from ..models import COMPONENTS, Project, Table
from ..sample import build_sample_project
from ..storage import PROJECT_FILTERS, ProjectFileError, load_project, save_project
from ..translation import build_ai_brief, default_brief_filename
from . import theme
from .dialogs import BriefDialog, ProjectDialog, RowDialog, TableDialog
from .diagram import DiagramView
from .widgets import FlatButton, InfoDialog, rounded_rect

DEFAULT_HINT = (
    "Drag any table to move it  \u00b7  double-click to edit  \u00b7  "
    "Ctrl+wheel to zoom  \u00b7  middle-drag to pan"
)


def _safe_filename(name: str) -> str:
    cleaned = "".join(
        ch if ch not in '<>:"/\\|?*' and ord(ch) >= 32 else "_" for ch in name
    ).strip(" .")
    return cleaned[:80].rstrip(" .") or "project"


def _enable_dpi_awareness() -> None:
    """Stop Windows from bitmap-scaling the window after Tk lays it out."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class MainWindow(tk.Tk):
    def __init__(
        self,
        *,
        initial_path: str | Path | None = None,
        sample: bool = False,
    ):
        _enable_dpi_awareness()
        super().__init__()
        self.project = Project()
        self.file_path: Path | None = None
        self.dirty = False
        self._undo: list[tuple[str, dict]] = []
        self._redo: list[tuple[str, dict]] = []
        self._status_text = DEFAULT_HINT
        self._status_tone = "muted"
        self._hover_text: str | None = None
        self._status_job = None
        self._status_seq = 0
        self._syncing_name = False

        theme.init_theme(self)
        theme.configure_styles(self)
        self.title(APP_NAME)
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = max(1040, min(1400, screen_w - 80))
        height = max(640, min(820, screen_h - 130))
        x = max(8, (screen_w - (width + 16)) // 2)
        y = max(6, (screen_h - (height + 62)) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(1080, width), min(640, height))
        self.configure(bg=theme.BG)
        self._set_icon()

        self._build_menus()
        self._build_header()
        self._build_body()
        self._build_statusbar()
        self._bind_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._sync_project()
        self._update_undo_menu()
        self._render_status()
        self._initial_job = self.after(
            80, lambda: self._initial_load(initial_path, sample)
        )

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def _set_icon(self) -> None:
        image = tk.PhotoImage(width=32, height=32)
        image.put(theme.ACCENT, to=(0, 0, 32, 32))
        for y in (8, 15, 22):
            image.put("#FFFFFF", to=(7, y, 25, y + 3))
        self._icon = image
        try:
            self.iconphoto(True, image)
        except tk.TclError:
            pass

    def _build_menus(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="New project\u2026", accelerator="Ctrl+N", command=self.new_project
        )
        file_menu.add_command(
            label="Open project\u2026", accelerator="Ctrl+O", command=self.open_project
        )
        file_menu.add_command(label="Open sample project", command=self.load_sample)
        file_menu.add_separator()
        file_menu.add_command(
            label="Save", accelerator="Ctrl+S", command=self.save_project
        )
        file_menu.add_command(
            label="Save as\u2026",
            accelerator="Ctrl+Shift+S",
            command=self.save_project_as,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Save AI brief as Markdown\u2026", command=self.export_brief
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0)
        self.edit_menu.add_command(
            label="Undo", accelerator="Ctrl+Z", command=self.undo
        )
        self.edit_menu.add_command(
            label="Redo", accelerator="Ctrl+Y", command=self.redo
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Project details\u2026", command=self.edit_project_details
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Add table\u2026", accelerator="Ctrl+T", command=self.add_table
        )
        self.edit_menu.add_command(
            label="Edit selected table\u2026", command=self.edit_selected_table
        )
        self.edit_menu.add_command(
            label="Duplicate selected table", command=self.duplicate_selected_table
        )
        self.edit_menu.add_command(
            label="Delete selected table\u2026",
            accelerator="Del",
            command=self.delete_selected_table,
        )
        menubar.add_cascade(label="Edit", menu=self.edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Auto layout", command=self.auto_layout)
        view_menu.add_command(label="Link rows", accelerator="Ctrl+L", command=self.toggle_link_mode)
        view_menu.add_separator()
        view_menu.add_command(label="Fit view", accelerator="Ctrl+0", command=self.fit_view)
        view_menu.add_command(label="Zoom in", accelerator="Ctrl++", command=self.zoom_in)
        view_menu.add_command(label="Zoom out", accelerator="Ctrl+-", command=self.zoom_out)
        view_menu.add_command(label="Reset zoom", command=self.reset_zoom)
        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Translate to AI brief\u2026",
            accelerator="Ctrl+Shift+T",
            command=self.show_brief,
        )
        tools_menu.add_command(
            label="Save AI brief as Markdown\u2026", command=self.export_brief
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Quick start", accelerator="F1", command=self.show_help)
        help_menu.add_command(label="About PMAI", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=theme.SURFACE)
        header.pack(fill="x", side="top")
        inner = tk.Frame(header, bg=theme.SURFACE)
        inner.pack(fill="x", padx=18, pady=9)

        logo = tk.Canvas(
            inner,
            width=38,
            height=38,
            bg=theme.SURFACE,
            highlightthickness=0,
        )
        logo.pack(side="left")
        rounded_rect(logo, 2, 2, 36, 36, 10, fill=theme.ACCENT, outline="")
        logo.create_text(
            19,
            19,
            text="P",
            fill="white",
            font=theme.px_font(18, "bold"),
        )
        brand = tk.Frame(inner, bg=theme.SURFACE)
        brand.pack(side="left", padx=(10, 0))
        tk.Label(
            brand,
            text=APP_NAME,
            bg=theme.SURFACE,
            fg=theme.INK,
            font=theme.font(12, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            brand,
            text=APP_TAGLINE.upper(),
            bg=theme.SURFACE,
            fg=theme.FAINT,
            font=theme.font(6, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        tk.Frame(inner, bg=theme.BORDER, width=1, height=34).pack(
            side="left", padx=16, fill="y"
        )

        project_box = tk.Frame(inner, bg=theme.SURFACE)
        project_box.pack(side="left")
        tk.Label(
            project_box,
            text="PROJECT",
            bg=theme.SURFACE,
            fg=theme.FAINT,
            font=theme.font(6, "bold"),
            anchor="w",
        ).pack(anchor="w")
        name_row = tk.Frame(project_box, bg=theme.SURFACE)
        name_row.pack(anchor="w")
        self.name_var = tk.StringVar(value=self.project.name)
        self.name_entry = tk.Entry(
            name_row,
            textvariable=self.name_var,
            bg=theme.SURFACE,
            fg=theme.INK,
            insertbackground=theme.ACCENT,
            selectbackground=theme.ACCENT_SOFT,
            selectforeground=theme.INK,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=theme.SURFACE,
            highlightcolor=theme.BORDER,
            font=theme.font(10, "bold"),
            width=26,
        )
        self.name_entry.pack(side="left", ipady=1)
        self.name_entry.bind("<FocusIn>", self._on_name_focus_in)
        self.name_entry.bind("<FocusOut>", lambda _e: self._commit_project_name())
        self.name_entry.bind("<Return>", self._on_name_return)
        self.name_entry.bind("<Escape>", self._on_name_escape)

        self.state_label = tk.Label(
            name_row,
            text="",
            bg=theme.SURFACE,
            fg=theme.MUTED,
            font=theme.font(7, "bold"),
            padx=9,
        )
        self.state_label.pack(side="left", padx=(4, 0))

        toolbar = tk.Frame(inner, bg=theme.SURFACE)
        toolbar.pack(side="right")
        self.add_btn = FlatButton(
            toolbar,
            text="+  Add table",
            command=self.add_table,
            variant="tonal",
            padx=14,
            pady=7,
        )
        self.add_btn.pack(side="left", padx=(0, 7))
        self.link_btn = FlatButton(
            toolbar,
            text="Link rows",
            command=self.toggle_link_mode,
            variant="ghost",
            padx=12,
            pady=7,
        )
        self.link_btn.pack(side="left", padx=(0, 7))
        self.arrange_btn = FlatButton(
            toolbar,
            text="Arrange",
            command=self.auto_layout,
            variant="ghost",
            padx=12,
            pady=7,
        )
        self.arrange_btn.pack(side="left", padx=(0, 7))
        self.fit_btn = FlatButton(
            toolbar,
            text="Fit",
            command=self.fit_view,
            variant="ghost",
            padx=12,
            pady=7,
        )
        self.fit_btn.pack(side="left", padx=(0, 16))
        self.save_btn = FlatButton(
            toolbar,
            text="Save",
            command=self.save_project,
            variant="ghost",
            padx=13,
            pady=7,
        )
        self.save_btn.pack(side="left", padx=(0, 7))
        self.translate_btn = FlatButton(
            toolbar,
            text="Translate  \u2192",
            command=self.show_brief,
            variant="primary",
            weight="bold",
            padx=15,
            pady=7,
        )
        self.translate_btn.pack(side="left")

        tk.Frame(self, bg=theme.BORDER, height=1).pack(fill="x", side="top")

    def _build_body(self) -> None:
        self.view = DiagramView(self, self)
        self.view.pack(fill="both", expand=True)

    def _build_statusbar(self) -> None:
        tk.Frame(self, bg=theme.BORDER, height=1).pack(fill="x", side="bottom")
        bar = tk.Frame(self, bg=theme.SURFACE)
        bar.pack(fill="x", side="bottom")
        inner = tk.Frame(bar, bg=theme.SURFACE)
        inner.pack(fill="x", padx=16, pady=5)
        self.status_dot = tk.Label(
            inner,
            text="\u25cf",
            bg=theme.SURFACE,
            fg=theme.ACCENT,
            font=theme.font(7),
        )
        self.status_dot.pack(side="left", padx=(0, 7))
        self.status_label = tk.Label(
            inner,
            text="",
            bg=theme.SURFACE,
            fg=theme.MUTED,
            font=theme.font(8),
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.zoom_button = FlatButton(
            inner,
            text="100%",
            command=self.reset_zoom,
            variant="subtle",
            size=8,
            padx=7,
            pady=1,
        )
        self.zoom_button.pack(side="right", padx=(5, 0))
        FlatButton(
            inner,
            text="+",
            command=self.zoom_in,
            variant="subtle",
            size=9,
            padx=7,
            pady=1,
        ).pack(side="right", padx=(5, 0))
        FlatButton(
            inner,
            text="\u2212",
            command=self.zoom_out,
            variant="subtle",
            size=9,
            padx=7,
            pady=1,
        ).pack(side="right", padx=(5, 0))
        FlatButton(
            inner,
            text="Fit",
            command=self.fit_view,
            variant="subtle",
            size=8,
            padx=7,
            pady=1,
        ).pack(side="right", padx=(10, 0))
        tk.Frame(inner, bg=theme.BORDER, width=1, height=18).pack(
            side="right", padx=(12, 8)
        )
        self.counts_label = tk.Label(
            inner,
            text="",
            bg=theme.SURFACE,
            fg=theme.MUTED,
            font=theme.font(8),
        )
        self.counts_label.pack(side="right")

    def _bind_shortcuts(self) -> None:
        def bind(sequence, callback):
            self.bind(sequence, callback)

        bind("<Control-n>", lambda _e: self.new_project())
        bind("<Control-o>", lambda _e: self.open_project())
        bind("<Control-s>", lambda _e: self.save_project())
        bind("<Control-S>", lambda _e: self.save_project_as())
        bind("<Control-Shift-S>", lambda _e: self.save_project_as())
        bind("<Control-Shift-s>", lambda _e: self.save_project_as())
        bind("<Control-z>", self._undo_shortcut)
        bind("<Control-Z>", self._undo_shortcut)
        bind("<Control-y>", self._redo_shortcut)
        bind("<Control-Y>", self._redo_shortcut)
        bind("<Control-Shift-Z>", self._redo_shortcut)
        bind("<Control-Shift-z>", self._redo_shortcut)
        bind("<Control-t>", lambda _e: self.add_table())
        bind("<Control-l>", lambda _e: self.toggle_link_mode())
        bind("<Control-0>", lambda _e: self.fit_view())
        bind("<Control-plus>", lambda _e: self.zoom_in())
        bind("<Control-equal>", lambda _e: self.zoom_in())
        bind("<Control-minus>", lambda _e: self.zoom_out())
        bind("<Control-Return>", lambda _e: self.show_brief())
        bind("<Control-Shift-T>", lambda _e: self.show_brief())
        bind("<Control-Shift-t>", lambda _e: self.show_brief())
        bind("<F1>", lambda _e: self.show_help())
        bind("<F5>", lambda _e: self.show_brief())
        bind("<Escape>", self._on_escape)

    # ------------------------------------------------------------------
    # startup / project lifecycle
    # ------------------------------------------------------------------

    def _initial_load(self, path: str | Path | None, sample: bool) -> None:
        if sample:
            self.load_sample(confirm=False)
        elif path:
            self._open_path(Path(path), confirm=False)
        else:
            self.view.fit_view()
            self.view.focus_set()
        self.update_zoom_ui(self.view.get_zoom())

    def _sync_project(self) -> None:
        self._syncing_name = True
        self.name_var.set(self.project.name)
        self._syncing_name = False
        self._update_title()
        self._update_counts()

    def _sync_name_only(self) -> None:
        self._syncing_name = True
        self.name_var.set(self.project.name)
        self._syncing_name = False

    def _update_title(self) -> None:
        marker = " *" if self.dirty else ""
        self.title(f"{self.project.name or 'Untitled Project'} \u2014 {APP_NAME}{marker}")
        if self.dirty:
            self.state_label.configure(text="\u25cf  Unsaved", fg=theme.WARNING)
        elif self.file_path:
            self.state_label.configure(text="\u25cf  Saved", fg=theme.SUCCESS)
        else:
            self.state_label.configure(text="\u25cf  Not saved", fg=theme.FAINT)

    def _update_counts(self) -> None:
        table_count = len(self.project.tables)
        row_count = self.project.total_rows()
        tables = "table" if table_count == 1 else "tables"
        rows = "row" if row_count == 1 else "rows"
        menu = len(self.project.menu_tables())
        fields = len(self.project.field_tables())
        pages = len(self.project.page_tables())
        page_word = "page" if pages == 1 else "pages"
        self.counts_label.configure(
            text=(
                f"{table_count} {tables}  \u00b7  {row_count} {rows}  \u00b7  "
                f"{menu} menu / {fields} fields / {pages} {page_word}"
            )
        )

    def mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()

    def _set_clean(self) -> None:
        self.dirty = False
        self._update_title()

    def _selected_table(self) -> Table | None:
        return self.project.get_table(self.view.selected_table_id)

    # ------------------------------------------------------------------
    # undo / redo
    # ------------------------------------------------------------------

    def push_undo(self, label: str, before: dict) -> None:
        self._undo.append((label, before))
        if len(self._undo) > 80:
            self._undo.pop(0)
        self._redo.clear()
        self._update_undo_menu()

    def _update_undo_menu(self) -> None:
        try:
            self.edit_menu.entryconfig(
                "Undo", state="normal" if self._undo else "disabled"
            )
            self.edit_menu.entryconfig(
                "Redo", state="normal" if self._redo else "disabled"
            )
        except tk.TclError:
            pass

    def _is_text_focus(self) -> bool:
        widget = self.focus_get()
        return isinstance(
            widget,
            (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox),
        )

    def _undo_shortcut(self, _event=None):
        if self._is_text_focus():
            return None
        self.undo()

    def _redo_shortcut(self, _event=None):
        if self._is_text_focus():
            return None
        self.redo()

    def undo(self) -> None:
        if not self._undo:
            self.set_status("Nothing to undo.", "muted", timeout=2500)
            return
        self._commit_project_name(silent=True)
        label, data = self._undo.pop()
        self._redo.append((label, self.project.to_dict()))
        self.project = Project.from_dict(data)
        self.dirty = True
        self._sync_project()
        self.view.refresh()
        self.view.ensure_visible(self.view.selected_table_id or "")
        self._update_undo_menu()
        self.set_status(f"Undid: {label.lower()}.", "info", timeout=3000)

    def redo(self) -> None:
        if not self._redo:
            self.set_status("Nothing to redo.", "muted", timeout=2500)
            return
        label, data = self._redo.pop()
        self._undo.append((label, self.project.to_dict()))
        self.project = Project.from_dict(data)
        self.dirty = True
        self._sync_project()
        self.view.refresh()
        self._update_undo_menu()
        self.set_status(f"Redid: {label.lower()}.", "info", timeout=3000)

    # ------------------------------------------------------------------
    # project name entry
    # ------------------------------------------------------------------

    def _on_name_focus_in(self, _event=None) -> None:
        self.name_entry.configure(
            highlightbackground=theme.BORDER_STRONG,
            highlightcolor=theme.ACCENT,
        )
        self.name_entry.select_range(0, "end")

    def _on_name_return(self, _event=None):
        self._commit_project_name()
        self.view.focus_set()
        return "break"

    def _on_name_escape(self, _event=None) -> None:
        self._sync_name_only()
        self.view.focus_set()

    def _commit_project_name(self, silent: bool = False) -> bool:
        if self._syncing_name:
            return False
        name = self.name_var.get().strip()
        if not name:
            self._sync_name_only()
            return False
        if name == self.project.name:
            return False
        before = self.project.to_dict()
        self.project.name = name
        self.push_undo("Rename project", before)
        self.mark_dirty()
        self._update_title()
        if not silent:
            self.set_status(f"Project renamed to \u201c{name}\u201d.", "success", timeout=3000)
        return True

    # ------------------------------------------------------------------
    # actions: tables
    # ------------------------------------------------------------------

    def add_table(self) -> None:
        if self.view.link_mode:
            self.view.set_link_mode(False)
        dialog = TableDialog(self, self.project)
        table = dialog.show()
        if table is None:
            self.view.focus_set()
            return
        before = self.project.to_dict()
        x, y = self.view.suggest_position(table)
        table.x, table.y = x, y
        self.project.add_table(table)
        self.project.normalize()
        self.push_undo("Add table", before)
        self.mark_dirty()
        self.view.refresh()
        self.view.selected_table_id = table.id
        self.view.selected_row_id = None
        self.view.ensure_visible(table.id)
        self._update_counts()
        noun = "component" if table.kind == COMPONENTS else "row"
        count = len(table.rows)
        self.set_status(
            f"Created table \u201c{table.name}\u201d with {count} "
            f"{noun}{'' if count == 1 else 's'}.",
            "success",
            timeout=3500,
        )
        self.view.focus_set()

    def edit_table(self, table_id: str | None) -> None:
        table = self.project.get_table(table_id)
        if not table:
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        dialog = TableDialog(self, self.project, table=table)
        result = dialog.show()
        if result is None:
            self.view.focus_set()
            return
        if result.to_dict() == table.to_dict():
            self.view.focus_set()
            return
        before = self.project.to_dict()
        index = self.project.tables.index(table)
        result.x, result.y = table.x, table.y
        self.project.tables[index] = result
        self.project.normalize()
        self.push_undo("Edit table", before)
        self.mark_dirty()
        self.view.refresh()
        self.view.ensure_visible(result.id)
        self.view.selected_table_id = result.id
        self.view.selected_row_id = None
        self._update_counts()
        self.set_status(f"Updated table \u201c{result.name}\u201d.", "success", timeout=3000)
        self.view.focus_set()

    def edit_selected_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.set_status("Select a table first, or double-click one.", "warning", timeout=3000)
            return
        self.edit_table(table.id)

    def edit_row(self, table_id: str, row_id: str) -> None:
        table = self.project.get_table(table_id)
        row = self.project.get_row(table_id, row_id)
        if not table or not row:
            return
        targets = [t for t in self.project.tables if t.id != table.id]
        noun = "component" if table.kind == COMPONENTS else "row"
        dialog = RowDialog(
            self,
            row=row.clone(),
            table_kind=table.kind,
            targets=targets,
            title=f"Edit {noun}",
        )
        result = dialog.show()
        if result is None:
            self.view.focus_set()
            return
        if result.to_dict() == row.to_dict():
            self.view.focus_set()
            return
        before = self.project.to_dict()
        for index, existing in enumerate(table.rows):
            if existing.id == row.id:
                table.rows[index] = result
                break
        self.project.normalize()
        self.push_undo("Edit row", before)
        self.mark_dirty()
        self.view.refresh()
        self.view.selected_table_id = table.id
        self.view.selected_row_id = result.id
        self._update_counts()
        self.set_status(f"Updated {noun} \u201c{result.name}\u201d.", "success", timeout=3000)
        self.view.focus_set()

    def set_row_link(self, table_id: str, row_id: str, target_id: str | None) -> bool:
        table = self.project.get_table(table_id)
        row = self.project.get_row(table_id, row_id)
        target = self.project.get_table(target_id) if target_id else None
        if not table or not row:
            return False
        if target_id and (target is None or target.id == table.id):
            return False
        if row.link_table_id == target_id:
            return False
        before = self.project.to_dict()
        row.link_table_id = target_id
        self.push_undo("Change link", before)
        self.mark_dirty()
        self.view.refresh()
        if target:
            self.set_status(
                f"Linked \u201c{row.name}\u201d \u2192 \u201c{target.name}\u201d.",
                "success",
                timeout=4000,
            )
        else:
            self.set_status(f"Removed link from \u201c{row.name}\u201d.", "info", timeout=3000)
        return True

    def duplicate_table(self, table_id: str) -> None:
        table = self.project.get_table(table_id)
        if not table:
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        clone = table.clone(new_ids=True)
        clone.name = self.project.unique_table_name(f"{table.name} copy")
        clone.x += 54
        clone.y += 54
        before = self.project.to_dict()
        self.project.add_table(clone)
        self.project.normalize()
        self.push_undo("Duplicate table", before)
        self.mark_dirty()
        self.view.refresh()
        self.view.selected_table_id = clone.id
        self.view.selected_row_id = None
        self.view.ensure_visible(clone.id)
        self._update_counts()
        self.set_status(f"Duplicated \u201c{table.name}\u201d.", "success", timeout=3000)

    def duplicate_selected_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.set_status("Select a table first.", "warning", timeout=3000)
            return
        self.duplicate_table(table.id)

    def delete_table(self, table_id: str) -> None:
        table = self.project.get_table(table_id)
        if not table:
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        incoming = sum(
            1
            for source in self.project.tables
            for row in source.rows
            if row.link_table_id == table_id
        )
        noun = "component" if table.kind == COMPONENTS else "row"
        count = len(table.rows)
        message = (
            f"Delete \u201c{table.name}\u201d?\n\n"
            f"This removes {count} {noun}{'' if count == 1 else 's'} and clears "
            f"{incoming} incoming link(s). You can undo this action."
        )
        if not messagebox.askyesno("Delete table", message, parent=self):
            return
        before = self.project.to_dict()
        self.project.remove_table(table_id)
        self.push_undo("Delete table", before)
        self.mark_dirty()
        if self.view.selected_table_id == table_id:
            self.view.selected_table_id = None
            self.view.selected_row_id = None
        self.view.refresh()
        self._update_counts()
        self.set_status(f"Deleted \u201c{table.name}\u201d.", "info", timeout=3000)
        self.view.focus_set()

    def delete_selected_table(self) -> None:
        table = self._selected_table()
        if not table:
            self.set_status("Select a table first.", "warning", timeout=3000)
            return
        self.delete_table(table.id)

    # ------------------------------------------------------------------
    # actions: view / layout
    # ------------------------------------------------------------------

    def auto_layout(self) -> None:
        if not self.project.tables:
            self.set_status("Add a table first.", "warning", timeout=3000)
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        before = self.project.to_dict()
        auto_layout(self.project)
        self.push_undo("Auto layout", before)
        self.mark_dirty()
        self.view.refresh()
        self.view.fit_view()
        self.set_status("Tables arranged from the link map.", "success", timeout=3000)

    def fit_view(self) -> None:
        self.view.fit_view()

    def zoom_in(self) -> None:
        self.view.zoom_in()

    def zoom_out(self) -> None:
        self.view.zoom_out()

    def reset_zoom(self) -> None:
        self.view.reset_zoom()

    def update_zoom_ui(self, zoom: float) -> None:
        if hasattr(self, "zoom_button"):
            self.zoom_button.configure(text=f"{round(zoom * 100)}%")

    def toggle_link_mode(self) -> None:
        if not self.project.tables:
            self.set_status("Add at least one table before linking rows.", "warning", timeout=3000)
            return
        self.view.toggle_link_mode()

    def on_link_mode_change(self, active: bool) -> None:
        self.link_btn.set_active(active)
        self.link_btn.configure(text="Linking\u2026" if active else "Link rows")

    def _on_escape(self, _event=None) -> None:
        if self.view.link_mode:
            self.view.set_link_mode(False)
        elif self.view.selected_table_id:
            self.view.selected_table_id = None
            self.view.selected_row_id = None
            self.view.redraw()

    # ------------------------------------------------------------------
    # actions: project details / translate / help
    # ------------------------------------------------------------------

    def edit_project_details(self) -> None:
        dialog = ProjectDialog(self, self.project)
        result = dialog.show()
        if not result:
            self.view.focus_set()
            return
        if (
            result["name"] == self.project.name
            and result["description"] == self.project.description
        ):
            self.view.focus_set()
            return
        before = self.project.to_dict()
        self.project.name = result["name"]
        self.project.description = result["description"]
        self.push_undo("Edit project details", before)
        self.mark_dirty()
        self._sync_name_only()
        self._update_title()
        self.set_status("Project details updated.", "success", timeout=3000)
        self.view.focus_set()

    def show_brief(self) -> None:
        self._commit_project_name(silent=True)
        if not self.project.tables:
            messagebox.showinfo(
                "Nothing to translate yet",
                "Add at least one table with rows or components, then translate it "
                "into an AI brief.",
                parent=self,
            )
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        brief = build_ai_brief(self.project)
        BriefDialog(self, self.project, brief).show()
        self.view.focus_set()

    def export_brief(self) -> None:
        self._commit_project_name(silent=True)
        if not self.project.tables:
            messagebox.showinfo(
                "Nothing to translate yet",
                "Add at least one table with rows or components before exporting a brief.",
                parent=self,
            )
            return
        initial = default_brief_filename(self.project)
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save AI brief",
            defaultextension=".md",
            initialfile=initial,
            initialdir=str(self.file_path.parent) if self.file_path else str(Path.home()),
            filetypes=[("Markdown", "*.md"), ("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(build_ai_brief(self.project), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Could not save brief", str(exc), parent=self)
            return
        self.set_status(f"Saved AI brief to {path}", "success", timeout=5000)

    def show_help(self) -> None:
        blocks = [
            ("Draw first, build later\n", "h"),
            (
                "PMAI is an offline sketchpad for app structure. Build a diagram of "
                "menus, data fields, and pages of UI components, then translate it "
                "into a brief an AI can follow.\n\n",
                None,
            ),
            ("Start with a project\n", "h"),
            (
                "Press Ctrl+N to give your project a name and a short description. "
                "These details become the opening of the AI brief.\n\n",
                None,
            ),
            ("1. Add a table\n", "h"),
            (
                "Choose Menu for navigation, Data fields for a modal / database "
                "model, or Page for a screen built from UI components. Give it a "
                "name and optional notes. Every row has a name, type and notes.\n\n",
                None,
            ),
            ("2. Add rows or components\n", "h"),
            (
                "Menu tables only allow Menu rows. Data-field tables let you pick a "
                "field type or type a custom one (Text, DateTime, Currency, "
                "Reference\u2026). Page tables use + Add Component with Button, "
                "TextBox, Text Area, Table, Tabs, or H1\u2013H6.\n\n",
                None,
            ),
            ("3. Link a row or component to a table\n", "h"),
            (
                "Use the Link rows tool, then click a row and then the target table. "
                "You can also right-click a row or edit it and choose Links to table. "
                "The arrow shows that the row opens or references the target.\n\n",
                None,
            ),
            ("4. Move things around\n", "h"),
            (
                "Drag any part of a card to move it. Wheel scrolls, middle-drag pans, "
                "Ctrl+wheel zooms. Auto layout arranges every table from the links.\n\n",
                None,
            ),
            ("5. Translate and save\n", "h"),
            (
                "Translate builds a Markdown brief with all tables, notes, links and "
                "implementation rules. Copy it into your AI tool. Save projects as "
                ".pmproj (readable JSON) or .bin (compressed).\n\n",
                None,
            ),
            ("Keyboard shortcuts\n", "h"),
            ("Ctrl+N", "mono"),
            ("  new project\n", None),
            ("Ctrl+T", "mono"),
            ("  add table\n", None),
            ("Ctrl+L", "mono"),
            ("  link rows\n", None),
            ("Ctrl+Shift+T", "mono"),
            ("  translate\n", None),
            ("Ctrl+S", "mono"),
            ("  save\n", None),
            ("Ctrl+Z / Ctrl+Y", "mono"),
            ("  undo / redo\n", None),
            ("Ctrl+0", "mono"),
            ("  fit view\n", None),
            ("Esc", "mono"),
            ("  leave link mode / clear selection\n", None),
        ]
        dialog = InfoDialog(
            self,
            "Quick start",
            "A two-minute tour of PMAI.",
            width=720,
            height=660,
        )
        dialog.set_rich_text(blocks)
        dialog.show()

    def show_about(self) -> None:
        blocks = [
            (f"PMAI {__version__}\n", "h"),
            ("Project \u2192 Prompt\n\n", "b"),
            (
                "PMAI turns a visual map of menus, data fields, and pages of UI "
                "components into a precise AI build brief. It is local, offline and "
                "dependency-free.\n\n",
                None,
            ),
            ("Formats\n", "h"),
            ("PMAI project (.pmproj)", "mono"),
            ("  readable JSON\n", None),
            ("PMAI binary (.bin)", "mono"),
            ("  gzip-compressed JSON with a magic header\n", None),
            ("AI brief (.md)", "mono"),
            ("  Markdown prompt\n\n", None),
            ("Built with Python and Tkinter.\n", "muted"),
        ]
        dialog = InfoDialog(
            self,
            "About PMAI",
            "A small offline tool for a big head start.",
            width=620,
            height=470,
        )
        dialog.set_rich_text(blocks)
        dialog.show()

    # ------------------------------------------------------------------
    # status bar
    # ------------------------------------------------------------------

    def set_status(self, text: str, tone: str = "info", timeout: int = 0) -> None:
        self._status_seq += 1
        seq = self._status_seq
        self._hover_text = None
        self._status_text = text
        self._status_tone = tone
        self._render_status()
        if self._status_job is not None:
            try:
                self.after_cancel(self._status_job)
            except tk.TclError:
                pass
            self._status_job = None
        if timeout:
            self._status_job = self.after(timeout, lambda: self._reset_status(seq))

    def _reset_status(self, seq: int) -> None:
        if seq != self._status_seq:
            return
        self._status_job = None
        self._status_text = DEFAULT_HINT
        self._status_tone = "muted"
        self._hover_text = None
        self._render_status()

    def set_hover_hint(self, text: str | None) -> None:
        if text == self._hover_text:
            return
        self._hover_text = text
        self._render_status()

    def _render_status(self) -> None:
        if self._hover_text:
            self.status_label.configure(text=self._hover_text, fg=theme.MUTED)
            self.status_dot.configure(fg=theme.ACCENT)
            return
        colors = {
            "info": theme.INK_SOFT,
            "success": theme.SUCCESS,
            "warning": theme.WARNING,
            "error": theme.DANGER,
            "muted": theme.MUTED,
        }
        dots = {
            "info": theme.ACCENT,
            "success": theme.SUCCESS,
            "warning": theme.WARNING,
            "error": theme.DANGER,
            "muted": theme.FAINT,
        }
        self.status_label.configure(
            text=self._status_text,
            fg=colors.get(self._status_tone, theme.MUTED),
        )
        self.status_dot.configure(fg=dots.get(self._status_tone, theme.FAINT))

    # ------------------------------------------------------------------
    # file operations
    # ------------------------------------------------------------------

    def new_project(self) -> None:
        if not self._confirm_discard():
            return

        dialog = ProjectDialog(self, Project(), creating=True)
        result = dialog.show()
        if not result:
            self.view.focus_set()
            return

        self.project = Project(
            name=result["name"],
            description=result["description"],
        )
        self.file_path = None
        self._undo.clear()
        self._redo.clear()
        self.view.selected_table_id = None
        self.view.selected_row_id = None
        self.view.link_source = None
        if self.view.link_mode:
            self.view.set_link_mode(False)
        self.view.refresh()
        self.view.fit_view()
        self._set_clean()
        self._sync_project()
        self._update_undo_menu()
        self.set_status("New project created.", "info", timeout=3000)
        self.view.focus_set()

    def _confirm_discard(self) -> bool:
        self._commit_project_name(silent=True)
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved changes",
            "Save changes to the current project before continuing?",
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            return self.save_project()
        return True

    def save_project(self) -> bool:
        self._commit_project_name(silent=True)
        if self.file_path is None:
            return self.save_project_as()
        try:
            saved = save_project(self.project, self.file_path)
        except ProjectFileError as exc:
            messagebox.showerror("Could not save project", str(exc), parent=self)
            return False
        self.file_path = saved
        self._set_clean()
        self._update_title()
        self.set_status(f"Saved to {saved}", "success", timeout=4000)
        return True

    def save_project_as(self) -> bool:
        self._commit_project_name(silent=True)
        initial = f"{_safe_filename(self.project.name)}.pmproj"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save project",
            defaultextension=".pmproj",
            initialfile=initial,
            initialdir=str(self.file_path.parent) if self.file_path else str(Path.home()),
            filetypes=PROJECT_FILTERS,
        )
        if not path:
            return False
        try:
            saved = save_project(self.project, path)
        except ProjectFileError as exc:
            messagebox.showerror("Could not save project", str(exc), parent=self)
            return False
        self.file_path = saved
        self._set_clean()
        self._update_title()
        self.set_status(
            f"Saved to {saved}" + (" (compressed binary)" if saved.suffix.lower() == ".bin" else ""),
            "success",
            timeout=4500,
        )
        return True

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Open PMAI project",
            initialdir=str(self.file_path.parent) if self.file_path else str(Path.home()),
            filetypes=PROJECT_FILTERS,
        )
        if not path:
            return
        self._open_path(Path(path), confirm=False)

    def _open_path(self, path: Path, *, confirm: bool = True) -> bool:
        if confirm and not self._confirm_discard():
            return False
        try:
            project = load_project(path)
        except ProjectFileError as exc:
            messagebox.showerror("Could not open project", str(exc), parent=self)
            return False
        if self.view.link_mode:
            self.view.set_link_mode(False)
        self.project = project
        self.file_path = path
        self._undo.clear()
        self._redo.clear()
        self.view.selected_table_id = None
        self.view.selected_row_id = None
        self._set_clean()
        self._sync_project()
        self._update_undo_menu()
        self.view.refresh()
        self.after_idle(self.view.fit_view)
        self.set_status(
            f"Opened {path.name} \u2014 {len(project.tables)} table(s).",
            "success",
            timeout=4000,
        )
        self.view.focus_set()
        return True

    def load_sample(self, confirm: bool = True) -> None:
        if confirm and not self._confirm_discard():
            return
        if self.view.link_mode:
            self.view.set_link_mode(False)
        self.project = build_sample_project()
        self.file_path = None
        self._undo.clear()
        self._redo.clear()
        self.view.selected_table_id = None
        self.view.selected_row_id = None
        self._sync_project()
        self.dirty = True
        self._update_title()
        self.view.refresh()
        self.after_idle(self.view.fit_view)
        self.set_status(
            "Sample project loaded. Move things around, then Translate or Save As.",
            "info",
            timeout=5000,
        )
        self.view.focus_set()

    def _on_close(self) -> None:
        if not self._confirm_discard():
            return
        if self._initial_job is not None:
            try:
                self.after_cancel(self._initial_job)
            except tk.TclError:
                pass
            self._initial_job = None
        try:
            self.destroy()
        except tk.TclError:
            pass
