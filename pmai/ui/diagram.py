"""The diagram canvas: draggable tables, arrows, zoom and link mode."""

from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass

from .. import cardmetrics
from ..models import COMPONENTS, Row, Table
from . import theme
from .widgets import FlatButton, rounded_rect

MIN_ZOOM = 0.35
MAX_ZOOM = 2.0
ZOOM_STEP = 1.15

KIND_PILL_LABELS = {
    "menu": "MENU",
    "fields": "FIELDS",
    "components": "PAGE",
}


@dataclass
class Hit:
    kind: str  # "header" | "row" | "body"
    table: Table
    row: Row | None = None


@dataclass
class DragState:
    table: Table
    start_x: float
    start_y: float
    origin_x: float
    origin_y: float
    before: dict
    moved: bool = False


@dataclass
class ArrowHead:
    tip_x: float
    tip_y: float
    base_x: float
    half: float
    color: str


class DiagramView(tk.Canvas):
    def __init__(self, parent, app):
        super().__init__(
            parent,
            bg=theme.BG,
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="arrow",
        )
        self.app = app
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.selected_table_id: str | None = None
        self.selected_row_id: str | None = None
        self.link_mode = False
        self.link_source: tuple[str, str] | None = None
        self._drag: DragState | None = None
        self._pending_pan: tuple[float, float, float, float] | None = None
        self._middle_pan: tuple[float, float, float, float] | None = None
        self._panning = False
        self._last_hint: str | None = None
        self._font_cache: dict[tuple[int, str], tkfont.Font] = {}
        self._redraw_job = None
        self._build_empty_state()
        self._bind_events()

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        self.bind("<Configure>", self._on_configure)
        self.bind("<ButtonPress-1>", self._on_left_press)
        self.bind("<B1-Motion>", self._on_left_drag)
        self.bind("<ButtonRelease-1>", self._on_left_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<ButtonPress-3>", self._on_right_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Shift-MouseWheel>", self._on_shift_wheel)
        self.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.bind("<ButtonPress-2>", self._on_middle_press)
        self.bind("<B2-Motion>", self._on_middle_drag)
        self.bind("<ButtonRelease-2>", self._on_middle_release)
        self.bind("<Delete>", self._on_delete)
        # Linux wheel events, harmless on Windows.
        self.bind("<Button-4>", lambda e: self._pan_by(0, 80))
        self.bind("<Button-5>", lambda e: self._pan_by(0, -80))

    def _build_empty_state(self) -> None:
        self.empty = tk.Frame(self, bg=theme.BG)
        illustration = tk.Canvas(
            self.empty,
            width=360,
            height=118,
            bg=theme.BG,
            highlightthickness=0,
            takefocus=0,
        )
        illustration.pack()
        self._draw_illustration(illustration)

        tk.Label(
            self.empty,
            text="PROJECT  \u2192  PROMPT",
            bg=theme.BG,
            fg=theme.ACCENT,
            font=theme.font(8, "bold"),
        ).pack(pady=(2, 8))
        tk.Label(
            self.empty,
            text="Design first. Then brief your AI.",
            bg=theme.BG,
            fg=theme.INK,
            font=theme.font(22, "bold"),
        ).pack()
        tk.Label(
            self.empty,
            text=(
                "Sketch menu tables, model your database fields, design pages of "
                "UI components, and connect rows with arrows. Translate the whole "
                "diagram into a precise build brief."
            ),
            bg=theme.BG,
            fg=theme.MUTED,
            font=theme.font(10),
            justify="center",
            wraplength=520,
        ).pack(pady=(8, 20))

        buttons = tk.Frame(self.empty, bg=theme.BG)
        buttons.pack()
        FlatButton(
            buttons,
            text="+  Add your first table",
            command=self.app.add_table,
            variant="primary",
            padx=18,
            pady=9,
        ).pack(side="left", padx=5)
        FlatButton(
            buttons,
            text="Open sample project",
            command=self.app.load_sample,
            variant="ghost",
            padx=18,
            pady=9,
        ).pack(side="left", padx=5)
        tk.Label(
            self.empty,
            text="Ctrl+T  add table     Ctrl+O  open project     Ctrl+L  link rows",
            bg=theme.BG,
            fg=theme.FAINT,
            font=theme.font(8),
        ).pack(pady=(22, 0))
        self.empty.place(relx=0.5, rely=0.47, anchor="center")
        self.empty.place_forget()

    def _draw_illustration(self, canvas: tk.Canvas) -> None:
        def mini_card(x, y, w, h, fg, bg, labels):
            rounded_rect(
                canvas, x + 2, y + 3, x + w + 2, y + h + 3, 8, fill="#E5EAF3"
            )
            rounded_rect(
                canvas, x, y, x + w, y + h, 8, fill="white", outline=theme.BORDER
            )
            rounded_rect(canvas, x, y, x + w, y + 18, 8, fill=bg, outline="")
            canvas.create_rectangle(x, y + 10, x + w, y + 18, fill=bg, outline="")
            rounded_rect(
                canvas, x + 9, y + 6, x + 12, y + 13, 1.5, fill=fg, outline=""
            )
            canvas.create_text(
                x + 17,
                y + 9,
                text=labels[0],
                anchor="w",
                fill=fg,
                font=theme.px_font(7, "bold"),
            )
            for index, line in enumerate(labels[1:]):
                yy = y + 28 + index * 12
                if yy + 5 > y + h:
                    break
                canvas.create_text(
                    x + 10,
                    yy,
                    text=line,
                    anchor="w",
                    fill=theme.INK_SOFT,
                    font=theme.px_font(7),
                )

        mini_card(
            28, 30, 118, 62, theme.MENU_FG, theme.MENU_BG, ["MENU", "Dashboard", "Billing"]
        )
        mini_card(
            222,
            20,
            118,
            82,
            theme.FIELDS_FG,
            theme.FIELDS_BG,
            ["FIELDS", "Invoice #", "Date", "Amount"],
        )
        points = []
        for index in range(25):
            t = index / 24
            x = 148 + (214 - 148) * t
            y = 62 - math.sin(t * math.pi) * 12
            points.extend((x, y))
        canvas.create_line(
            points,
            fill=theme.LINK_COLOR,
            width=2,
            smooth=True,
            arrow=tk.LAST,
            arrowshape=(7, 8, 3),
        )

    # ------------------------------------------------------------------
    # coordinates & drawing
    # ------------------------------------------------------------------

    def _sx(self, world_x: float) -> float:
        return (world_x - self.pan_x) * self.zoom

    def _sy(self, world_y: float) -> float:
        return (world_y - self.pan_y) * self.zoom

    def _world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        return (
            screen_x / self.zoom + self.pan_x,
            screen_y / self.zoom + self.pan_y,
        )

    def _font(self, px: float, weight: str = "normal") -> tkfont.Font:
        size = max(6, int(round(px)))
        key = (size, weight)
        font = self._font_cache.get(key)
        if font is None:
            font = tkfont.Font(
                family=theme.UI_FAMILY,
                size=-size,
                weight=weight,
            )
            self._font_cache[key] = font
        return font

    def _fit_text(self, text: str, px: float, width: float, weight: str = "normal") -> str:
        if width <= 2:
            return ""
        value = str(text or "").replace("\n", " ").strip()
        font = self._font(px, weight)
        if font.measure(value) <= width:
            return value
        suffix = "\u2026"
        low, high = 0, len(value)
        while low < high:
            mid = (low + high + 1) // 2
            if font.measure(value[:mid].rstrip() + suffix) <= width:
                low = mid
            else:
                high = mid - 1
        return (value[:low].rstrip() + suffix) if low else suffix

    def _on_configure(self, _event=None) -> None:
        if self._redraw_job is not None:
            try:
                self.after_cancel(self._redraw_job)
            except tk.TclError:
                pass
        self._redraw_job = self.after(25, self._redraw_once)

    def _redraw_once(self) -> None:
        self._redraw_job = None
        self.redraw()

    def refresh(self) -> None:
        if self.app.project.get_table(self.selected_table_id) is None:
            self.selected_table_id = None
            self.selected_row_id = None
        if self.link_source and self.app.project.get_row(*self.link_source) is None:
            self.link_source = None
        if self.app.project.tables:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.47, anchor="center")
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self._draw_grid(width, height)
        arrowheads, ports = self._draw_arrows()
        for table in self.app.project.tables:
            self._draw_card(table)
        for head in arrowheads:
            self.create_polygon(
                head.base_x,
                head.tip_y - head.half,
                head.base_x,
                head.tip_y + head.half,
                head.tip_x,
                head.tip_y,
                fill=head.color,
                outline=head.color,
            )
        for x, y, color in ports:
            radius = max(2.4, 3.4 * self.zoom)
            self.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=theme.SURFACE,
                outline=color,
                width=max(1.2, 1.8 * self.zoom),
            )
        self._draw_selection()
        if not self.app.project.tables:
            self.empty.place(relx=0.5, rely=0.47, anchor="center")
        else:
            self.empty.place_forget()

    def _draw_grid(self, width: int, height: int) -> None:
        grid = 72.0
        step = grid * self.zoom
        while step < 30:
            grid *= 2
            step = grid * self.zoom
        first_x = math.floor(self.pan_x / grid) * grid
        first_y = math.floor(self.pan_y / grid) * grid
        max_x = self.pan_x + width / self.zoom
        max_y = self.pan_y + height / self.zoom
        dot = max(0.8, min(1.5, self.zoom))
        y = first_y
        while y <= max_y + grid:
            x = first_x
            while x <= max_x + grid:
                sx, sy = self._sx(x), self._sy(y)
                if 0 < sx < width and 0 < sy < height:
                    self.create_oval(
                        sx - dot / 2,
                        sy - dot / 2,
                        sx + dot / 2,
                        sy + dot / 2,
                        fill=theme.GRID_DOT,
                        outline="",
                    )
                x += grid
            y += grid

    def _card_screen_rect(self, table: Table):
        w, h = cardmetrics.card_size(table)
        return (
            self._sx(table.x),
            self._sy(table.y),
            self._sx(table.x + w),
            self._sy(table.y + h),
        )

    def _draw_card(self, table: Table) -> None:
        width, height = cardmetrics.card_size(table)
        x1, y1 = self._sx(table.x), self._sy(table.y)
        x2, y2 = self._sx(table.x + width), self._sy(table.y + height)
        vw, vh = self.winfo_width(), self.winfo_height()
        if x2 < -80 or y2 < -80 or x1 > vw + 80 or y1 > vh + 80:
            return
        z = self.zoom
        pad = cardmetrics.PAD * z
        header_h = cardmetrics.HEADER_H * z
        col_h = cardmetrics.COL_H * z
        row_h = cardmetrics.ROW_H * z
        kind_fg, kind_bg = theme.kind_colors(table.kind)
        selected = table.id == self.selected_table_id

        rounded_rect(
            self,
            x1 + 4 * z,
            y1 + 6 * z,
            x2 + 4 * z,
            y2 + 6 * z,
            15 * z,
            fill="#E4EAF4",
            outline="",
        )
        rounded_rect(
            self,
            x1,
            y1,
            x2,
            y2,
            15 * z,
            fill=theme.SURFACE,
            outline=theme.BORDER_STRONG if selected else theme.BORDER,
            width=max(1.0, 1.15 * z),
        )

        # header
        rounded_rect(
            self,
            x1 + pad,
            y1 + 19 * z,
            x1 + pad + 3.5 * z,
            y1 + 35 * z,
            1.8 * z,
            fill=kind_fg,
            outline="",
        )
        title_x = x1 + pad + 12 * z
        pill_text = KIND_PILL_LABELS.get(table.kind, "FIELDS")
        pill_font_px = 8.8 * z
        pill_font = self._font(pill_font_px, "bold")
        pill_w = pill_font.measure(pill_text) + 17 * z
        pill_h = 20 * z
        pill_x2 = x1 + width * z - pad
        pill_x1 = pill_x2 - pill_w
        pill_y1 = y1 + header_h / 2 - pill_h / 2
        title_limit = pill_x1 - 12 * z - title_x
        title = self._fit_text(
            table.name or "Untitled table",
            15 * z,
            title_limit,
            "bold",
        )
        self.create_text(
            title_x,
            y1 + header_h / 2,
            text=title,
            anchor="w",
            fill=theme.INK,
            font=theme.px_font(15 * z, "bold"),
        )
        rounded_rect(
            self,
            pill_x1,
            pill_y1,
            pill_x2,
            pill_y1 + pill_h,
            pill_h / 2,
            fill=kind_bg,
            outline="",
        )
        self.create_text(
            (pill_x1 + pill_x2) / 2,
            pill_y1 + pill_h / 2,
            text=pill_text,
            fill=kind_fg,
            font=theme.px_font(pill_font_px, "bold"),
        )
        self.create_line(
            x1 + 1,
            y1 + header_h,
            x2 - 1,
            y1 + header_h,
            fill=theme.BORDER,
            width=max(1, z),
        )

        # column header band
        self.create_rectangle(
            x1 + 1,
            y1 + header_h,
            x2 - 1,
            y1 + header_h + col_h,
            fill=theme.SURFACE_ALT,
            outline="",
        )
        col_y = y1 + header_h + col_h / 2
        for label, wx in (
            ("NAME", cardmetrics.NAME_X),
            ("TYPE", cardmetrics.TYPE_X),
            ("NOTES", cardmetrics.NOTES_X),
        ):
            self.create_text(
                x1 + wx * z,
                col_y,
                text=label,
                anchor="w",
                fill=theme.MUTED,
                font=theme.px_font(8.8 * z, "bold"),
            )
        self.create_line(
            x1 + 1,
            y1 + header_h + col_h,
            x2 - 1,
            y1 + header_h + col_h,
            fill=theme.BORDER,
            width=max(1, z),
        )

        row_top = y1 + header_h + col_h
        visible = cardmetrics.visible_rows(table)
        for index, row in enumerate(visible):
            top = row_top + index * row_h
            bottom = top + row_h
            is_selected = selected and row.id == self.selected_row_id
            if is_selected:
                self.create_rectangle(
                    x1 + 1.5,
                    top,
                    x2 - 1.5,
                    bottom,
                    fill=theme.ACCENT_SOFT,
                    outline="",
                )
                self.create_rectangle(
                    x1 + 1.5,
                    top + 3 * z,
                    x1 + 1.5 + 2.5 * z,
                    bottom - 3 * z,
                    fill=theme.ACCENT,
                    outline="",
                )
            if index < len(visible) - 1:
                self.create_line(
                    x1 + pad,
                    bottom,
                    x2 - pad,
                    bottom,
                    fill=theme.BORDER,
                    width=max(1, 0.8 * z),
                )
            cy = top + row_h / 2
            name = self._fit_text(
                row.name or "(unnamed)",
                12.2 * z,
                (cardmetrics.NAME_W - (8 if is_selected else 0)) * z,
            )
            self.create_text(
                x1 + cardmetrics.NAME_X * z + (8 * z if is_selected else 0),
                cy,
                text=name,
                anchor="w",
                fill=theme.INK,
                font=theme.px_font(12.2 * z),
            )
            # type pill
            if table.kind == "menu":
                type_text = "Menu"
            elif table.kind == COMPONENTS:
                type_text = row.type or "Button"
            else:
                type_text = row.type or "Text"
            fg, bg = theme.type_colors(type_text)
            chip_font_px = 9.0 * z
            chip_font = self._font(chip_font_px, "bold")
            chip_text = self._fit_text(
                type_text, chip_font_px, cardmetrics.TYPE_W * z - 14 * z, "bold"
            )
            chip_w = chip_font.measure(chip_text) + 14 * z
            chip_h = 19 * z
            chip_x = x1 + cardmetrics.TYPE_X * z
            rounded_rect(
                self,
                chip_x,
                cy - chip_h / 2,
                chip_x + chip_w,
                cy + chip_h / 2,
                chip_h / 2,
                fill=bg,
                outline="",
            )
            self.create_text(
                chip_x + chip_w / 2,
                cy,
                text=chip_text,
                fill=fg,
                font=theme.px_font(chip_font_px, "bold"),
            )
            notes_limit = cardmetrics.NOTES_W * z - (12 * z if row.link_table_id else 0)
            notes = self._fit_text(row.notes or "", 10.8 * z, notes_limit)
            if notes:
                self.create_text(
                    x1 + cardmetrics.NOTES_X * z,
                    cy,
                    text=notes,
                    anchor="w",
                    fill=theme.NOTE_TEXT,
                    font=theme.px_font(10.8 * z),
                )

        after_rows = row_top + len(visible) * row_h
        noun = "component" if table.kind == COMPONENTS else "row"
        plural = f"{noun}s"
        if not table.rows:
            self.create_text(
                x1 + width * z / 2,
                after_rows + cardmetrics.EMPTY_H * z / 2,
                text=f"No {plural} yet \u2014 double-click to add some",
                fill=theme.FAINT,
                font=theme.px_font(9.6 * z),
            )
            after_rows += cardmetrics.EMPTY_H * z
        elif len(table.rows) > cardmetrics.MAX_VISIBLE_ROWS:
            hidden = len(table.rows) - cardmetrics.MAX_VISIBLE_ROWS
            self.create_text(
                x1 + width * z / 2,
                after_rows + 14 * z,
                text=f"+{hidden} more {plural} \u2014 open the table to edit",
                fill=theme.FAINT,
                font=theme.px_font(9.2 * z),
            )
            after_rows += 28 * z

        note_lines = cardmetrics.note_lines(table.notes)
        if note_lines:
            note_top = after_rows + cardmetrics.NOTE_TOP * z
            self.create_line(
                x1 + pad,
                note_top,
                x2 - pad,
                note_top,
                fill=theme.BORDER,
                width=max(1, 0.8 * z),
            )
            self.create_text(
                x1 + pad,
                note_top + 11 * z,
                text="NOTES",
                anchor="w",
                fill=theme.FAINT,
                font=theme.px_font(8.6 * z, "bold"),
            )
            line_y = note_top + cardmetrics.NOTE_TITLE_H * z
            for line in note_lines:
                if line:
                    self.create_text(
                        x1 + pad,
                        line_y,
                        text=self._fit_text(line, 11.0 * z, (width - 2 * cardmetrics.PAD) * z),
                        anchor="w",
                        fill=theme.NOTE_TEXT,
                        font=theme.px_font(11.0 * z),
                    )
                line_y += cardmetrics.NOTE_LINE_H * z

    def _draw_selection(self) -> None:
        table = self.app.project.get_table(self.selected_table_id)
        if not table:
            return
        width, height = cardmetrics.card_size(table)
        x1, y1 = self._sx(table.x), self._sy(table.y)
        x2, y2 = self._sx(table.x + width), self._sy(table.y + height)
        rounded_rect(
            self,
            x1 - 2,
            y1 - 2,
            x2 + 2,
            y2 + 2,
            16 * self.zoom,
            fill="",
            outline=theme.ACCENT,
            width=2,
        )

    # ------------------------------------------------------------------
    # arrows
    # ------------------------------------------------------------------

    def _draw_arrows(self):
        arrowheads: list[ArrowHead] = []
        ports: list[tuple[float, float, str]] = []
        z = self.zoom
        for table in self.app.project.tables:
            visible = cardmetrics.visible_rows(table)
            for index, row in enumerate(visible):
                target = self.app.project.get_table(row.link_table_id)
                if not target:
                    continue
                highlight = row.id == self.selected_row_id and table.id == self.selected_table_id
                color = theme.LINK_SELECTED if highlight else theme.LINK_COLOR
                width = max(1.6, (2.6 if highlight else 2.0) * z)
                tw, th = cardmetrics.card_size(target)
                source_cy_world = (
                    table.y
                    + cardmetrics.HEADER_H
                    + cardmetrics.COL_H
                    + index * cardmetrics.ROW_H
                    + cardmetrics.ROW_H / 2
                )
                target_cy_world = target.y + th / 2
                direction = 1 if (target.x + tw / 2) >= (table.x + cardmetrics.CARD_W / 2) else -1
                sx = self._sx(table.x + (cardmetrics.CARD_W if direction == 1 else 0))
                tx = self._sx(target.x + (0 if direction == 1 else tw))
                sy = self._sy(source_cy_world)
                ty_top = self._sy(target.y)
                ty_bottom = self._sy(target.y + th)
                low, high = ty_top + 24 * z, ty_bottom - 24 * z
                ty = ty_bottom / 2 + ty_top / 2 if low > high else min(max(sy, low), high)
                distance = abs(tx - sx)
                ctrl = max(46 * z, min(190 * z, distance * 0.45))
                c1x = sx + direction * ctrl
                c2x = tx - direction * ctrl
                length = max(7.5, 10.5 * z)
                half = max(3.5, 5.0 * z)
                base_x = tx - direction * length
                points: list[float] = []
                for step in range(29):
                    t = step / 28
                    mt = 1 - t
                    x = (
                        mt * mt * mt * sx
                        + 3 * mt * mt * t * c1x
                        + 3 * mt * t * t * c2x
                        + t * t * t * base_x
                    )
                    y = (
                        mt * mt * mt * sy
                        + 3 * mt * mt * t * sy
                        + 3 * mt * t * t * ty
                        + t * t * t * ty
                    )
                    points.extend((x, y))
                self.create_line(
                    points,
                    fill=color,
                    width=width,
                    smooth=False,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                )
                arrowheads.append(ArrowHead(tx, ty, base_x, half, color))
                ports.append((sx, sy, color))
        return arrowheads, ports

    # ------------------------------------------------------------------
    # hit testing and selection
    # ------------------------------------------------------------------

    def _hit_test(self, screen_x: float, screen_y: float) -> Hit | None:
        wx, wy = self._world(screen_x, screen_y)
        for table in reversed(self.app.project.tables):
            width, height = cardmetrics.card_size(table)
            if table.x <= wx <= table.x + width and table.y <= wy <= table.y + height:
                if wy < table.y + cardmetrics.HEADER_H:
                    return Hit("header", table)
                if wy < table.y + cardmetrics.HEADER_H + cardmetrics.COL_H:
                    return Hit("header", table)
                rows_top = table.y + cardmetrics.HEADER_H + cardmetrics.COL_H
                visible = cardmetrics.visible_rows(table)
                for index, row in enumerate(visible):
                    top = rows_top + index * cardmetrics.ROW_H
                    if top <= wy <= top + cardmetrics.ROW_H:
                        return Hit("row", table, row)
                return Hit("body", table)
        return None

    def _select(self, table: Table | None, row: Row | None = None) -> None:
        self.selected_table_id = table.id if table else None
        self.selected_row_id = row.id if row else None

    # ------------------------------------------------------------------
    # mouse: selection, dragging, panning
    # ------------------------------------------------------------------

    def _on_left_press(self, event) -> None:
        self.focus_set()
        hit = self._hit_test(event.x, event.y)
        if self.link_mode:
            self._handle_link_click(hit)
            return
        self._pending_pan = None
        self._panning = False
        if hit is None:
            self._drag = None
            self._pending_pan = (event.x, event.y, self.pan_x, self.pan_y)
            return
        self._select(hit.table, hit.row if hit.kind == "row" else None)
        self._drag = DragState(
            table=hit.table,
            start_x=event.x,
            start_y=event.y,
            origin_x=hit.table.x,
            origin_y=hit.table.y,
            before=self.app.project.to_dict(),
        )
        self.redraw()

    def _on_left_drag(self, event) -> None:
        if self.link_mode:
            return
        if self._drag is not None:
            dx = event.x - self._drag.start_x
            dy = event.y - self._drag.start_y
            if not self._drag.moved and (abs(dx) > 4 or abs(dy) > 4):
                self._drag.moved = True
                self.configure(cursor="fleur")
            if self._drag.moved:
                self._drag.table.x = self._drag.origin_x + dx / self.zoom
                self._drag.table.y = self._drag.origin_y + dy / self.zoom
                self.redraw()
            return
        if self._pending_pan is not None:
            start_x, start_y, pan_x, pan_y = self._pending_pan
            dx = event.x - start_x
            dy = event.y - start_y
            if not self._panning and (abs(dx) > 4 or abs(dy) > 4):
                self._panning = True
                self.configure(cursor="fleur")
            if self._panning:
                self.pan_x = pan_x - dx / self.zoom
                self.pan_y = pan_y - dy / self.zoom
                self.redraw()

    def _on_left_release(self, _event) -> None:
        if self.link_mode:
            return
        if self._drag is not None:
            if self._drag.moved:
                self.app.push_undo("Move table", self._drag.before)
                self.app.mark_dirty()
                self.app.set_status(
                    f"Moved \u201c{self._drag.table.name}\u201d.", "info", timeout=2500
                )
            self._drag = None
        if self._pending_pan is not None and not self._panning:
            self._select(None, None)
            self.redraw()
        self._pending_pan = None
        self._panning = False
        self.configure(cursor="arrow")
        self._update_hover_hint(_event)

    def _on_middle_press(self, event) -> None:
        self.focus_set()
        self._middle_pan = (event.x, event.y, self.pan_x, self.pan_y)
        self.configure(cursor="fleur")

    def _on_middle_drag(self, event) -> None:
        if not self._middle_pan:
            return
        start_x, start_y, pan_x, pan_y = self._middle_pan
        self.pan_x = pan_x - (event.x - start_x) / self.zoom
        self.pan_y = pan_y - (event.y - start_y) / self.zoom
        self.redraw()

    def _on_middle_release(self, _event) -> None:
        self._middle_pan = None
        self.configure(cursor="arrow")

    def _on_delete(self, _event=None) -> None:
        if self.selected_table_id:
            self.app.delete_table(self.selected_table_id)

    # ------------------------------------------------------------------
    # double click & context menu
    # ------------------------------------------------------------------

    def _on_double_click(self, event) -> None:
        if self.link_mode:
            return
        self._drag = None
        hit = self._hit_test(event.x, event.y)
        if not hit:
            return
        if hit.kind == "row" and hit.row:
            table_id, row_id = hit.table.id, hit.row.id
            self.after_idle(lambda: self.app.edit_row(table_id, row_id))
        else:
            table_id = hit.table.id
            self.after_idle(lambda: self.app.edit_table(table_id))

    def _on_right_click(self, event) -> None:
        self.focus_set()
        hit = self._hit_test(event.x, event.y)
        menu = tk.Menu(self, tearoff=0)
        if hit is None:
            menu.add_command(label="Add table\u2026", command=self.app.add_table)
            menu.add_separator()
            menu.add_command(label="Auto layout", command=self.app.auto_layout)
            menu.add_command(label="Fit view", command=self.fit_view)
        else:
            self._select(hit.table, hit.row if hit.kind == "row" else None)
            self.redraw()
            if hit.kind == "row" and hit.row:
                row = hit.row
                menu.add_command(
                    label="Edit row\u2026",
                    command=lambda: self.app.edit_row(hit.table.id, row.id),
                )
                targets = [t for t in self.app.project.tables if t.id != hit.table.id]
                link_menu = tk.Menu(menu, tearoff=0)
                if targets:
                    for target in targets:
                        check = "\u2713  " if row.link_table_id == target.id else "\u2003\u2002"
                        link_menu.add_command(
                            label=f"{check}{target.name}  ({target.kind_short})",
                            command=lambda t=target.id: self.app.set_row_link(
                                hit.table.id, row.id, t
                            ),
                        )
                    if row.link_table_id:
                        link_menu.add_separator()
                        link_menu.add_command(
                            label="Remove link",
                            command=lambda: self.app.set_row_link(
                                hit.table.id, row.id, None
                            ),
                        )
                else:
                    link_menu.add_command(label="No other tables", state="disabled")
                menu.add_cascade(label="Link to table", menu=link_menu)
                if row.link_table_id and self.app.project.get_table(row.link_table_id):
                    menu.add_command(
                        label="Go to linked table",
                        command=lambda: self.center_on_table(row.link_table_id),
                    )
                menu.add_separator()
            menu.add_command(
                label="Edit table\u2026",
                command=lambda: self.app.edit_table(hit.table.id),
            )
            menu.add_command(
                label="Duplicate table",
                command=lambda: self.app.duplicate_table(hit.table.id),
            )
            menu.add_separator()
            menu.add_command(label="Auto layout", command=self.app.auto_layout)
            menu.add_command(label="Fit view", command=self.fit_view)
            menu.add_separator()
            menu.add_command(
                label="Delete table\u2026",
                command=lambda: self.app.delete_table(hit.table.id),
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # hover hints
    # ------------------------------------------------------------------

    def _on_motion(self, event) -> None:
        if self._drag is not None and self._drag.moved:
            self.configure(cursor="fleur")
            return
        if self._panning:
            return
        hit = self._hit_test(event.x, event.y)
        if self.link_mode:
            self.configure(cursor="hand2" if hit else "crosshair")
            self.app.set_hover_hint(None)
            return
        if hit is None:
            self.configure(cursor="arrow")
            self._set_hint(None)
            return
        self.configure(cursor="fleur")
        if hit.kind == "row" and hit.row:
            target = self.app.project.get_table(hit.row.link_table_id)
            if target:
                hint = (
                    f"Row \u201c{hit.row.name}\u201d \u2192 \u201c{target.name}\u201d. "
                    "Drag to move the table, double-click to edit the row."
                )
            else:
                hint = (
                    f"Row \u201c{hit.row.name}\u201d. Drag to move the table, "
                    "double-click to edit the row."
                )
        else:
            hint = (
                f"Table \u201c{hit.table.name}\u201d. Drag anywhere on the card to move it, "
                "double-click to edit."
            )
        self._set_hint(hint)

    def _set_hint(self, hint: str | None) -> None:
        if hint == self._last_hint:
            return
        self._last_hint = hint
        self.app.set_hover_hint(hint)

    def _update_hover_hint(self, event) -> None:
        if event is not None:
            self._on_motion(event)

    def _on_leave(self, _event=None) -> None:
        if not (self._drag and self._drag.moved):
            self.configure(cursor="arrow")
        self._set_hint(None)

    # ------------------------------------------------------------------
    # link mode
    # ------------------------------------------------------------------

    def set_link_mode(self, active: bool) -> None:
        if self.link_mode == active:
            return
        self.link_mode = active
        self.link_source = None
        self._drag = None
        self._set_hint(None)
        self.app.set_hover_hint(None)
        self.configure(cursor="crosshair" if active else "arrow")
        if active:
            self.app.set_status(
                "Link mode \u2014 click a row, then click the target table. Esc to cancel.",
                "info",
            )
        else:
            self.app.set_status("Link mode off.", "info", timeout=2500)
        self.app.on_link_mode_change(active)
        self.redraw()

    def toggle_link_mode(self) -> None:
        self.set_link_mode(not self.link_mode)

    def _handle_link_click(self, hit: Hit | None) -> None:
        if hit is None:
            if self.link_source:
                self.link_source = None
                self.selected_row_id = None
                self.app.set_status(
                    "Link cancelled. Click a row to start again, or Esc to exit link mode.",
                    "info",
                )
                self.redraw()
            return
        if self.link_source is None:
            if hit.kind == "row" and hit.row:
                self.link_source = (hit.table.id, hit.row.id)
                self._select(hit.table, hit.row)
                self.app.set_status(
                    f"Now click the table that \u201c{hit.row.name}\u201d should link to.",
                    "info",
                )
                self.redraw()
            else:
                self.app.set_status("Pick a row to start a link.", "warning", timeout=3000)
            return
        source_table = self.app.project.get_table(self.link_source[0])
        source_row = self.app.project.get_row(*self.link_source)
        if not source_table or not source_row:
            self.link_source = None
            return
        if hit.table.id == source_table.id:
            self.app.set_status("A row cannot link to its own table.", "warning", timeout=3000)
            return
        previous = source_row.link_table_id
        created = self.app.set_row_link(source_table.id, source_row.id, hit.table.id)
        self.link_source = None
        self.selected_row_id = source_row.id
        if created:
            self.app.set_status(
                f"Linked \u201c{source_row.name}\u201d \u2192 \u201c{hit.table.name}\u201d. "
                "Pick another row, or press Esc to finish.",
                "success",
            )
        elif previous == hit.table.id:
            self.app.set_status(
                "That link already exists. Pick another row or target.", "info", timeout=3000
            )
        self.redraw()

    # ------------------------------------------------------------------
    # zoom & pan
    # ------------------------------------------------------------------

    def get_zoom(self) -> float:
        return self.zoom

    def _notify_zoom(self) -> None:
        try:
            self.app.update_zoom_ui(self.zoom)
        except AttributeError:
            pass

    def set_zoom(self, value: float, anchor: tuple[float, float] | None = None) -> None:
        value = max(MIN_ZOOM, min(MAX_ZOOM, value))
        if abs(value - self.zoom) < 0.0001:
            return
        if anchor is None:
            anchor = (self.winfo_width() / 2, self.winfo_height() / 2)
        wx, wy = self._world(*anchor)
        self.zoom = value
        self.pan_x = wx - anchor[0] / self.zoom
        self.pan_y = wy - anchor[1] / self.zoom
        self.redraw()
        self._notify_zoom()

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom * ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom / ZOOM_STEP)

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)

    def _on_wheel(self, event) -> None:
        delta = event.delta
        if delta == 0:
            return
        self._pan_by(0, -(delta / 120) * 72)
        return "break"

    def _on_shift_wheel(self, event) -> None:
        delta = event.delta
        if delta == 0:
            return
        self._pan_by(-(delta / 120) * 90, 0)
        return "break"

    def _on_ctrl_wheel(self, event) -> None:
        if event.delta == 0:
            return
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self.set_zoom(self.zoom * factor, (event.x, event.y))
        return "break"

    def _pan_by(self, dx_screen: float, dy_screen: float) -> None:
        self.pan_x += dx_screen / self.zoom
        self.pan_y += dy_screen / self.zoom
        self.redraw()

    def fit_view(self) -> None:
        if not self.app.project.tables:
            self.zoom = 1.0
            self.pan_x = 0.0
            self.pan_y = 0.0
            self.redraw()
            self._notify_zoom()
            return
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 80 or height < 80:
            self.after(60, self.fit_view)
            return
        bounds = self._content_bounds()
        if not bounds:
            return
        min_x, min_y, max_x, max_y = bounds
        content_w = max(1.0, max_x - min_x)
        content_h = max(1.0, max_y - min_y)
        margin = 58
        zoom = min(
            (width - margin * 2) / content_w,
            (height - margin * 2) / content_h,
            1.12,
        )
        self.zoom = max(MIN_ZOOM, zoom)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.pan_x = center_x - width / (2 * self.zoom)
        self.pan_y = center_y - height / (2 * self.zoom)
        self.redraw()
        self._notify_zoom()

    def _content_bounds(self):
        if not self.app.project.tables:
            return None
        min_x = min(t.x for t in self.app.project.tables)
        min_y = min(t.y for t in self.app.project.tables)
        max_x = max(t.x + cardmetrics.CARD_W for t in self.app.project.tables)
        max_y = max(
            t.y + cardmetrics.card_size(t)[1] for t in self.app.project.tables
        )
        return min_x, min_y, max_x, max_y

    def center_on_table(self, table_id: str) -> None:
        table = self.app.project.get_table(table_id)
        if not table:
            return
        width, height = cardmetrics.card_size(table)
        vw, vh = self.winfo_width(), self.winfo_height()
        self.pan_x = table.x + width / 2 - vw / (2 * self.zoom)
        self.pan_y = table.y + height / 2 - vh / (2 * self.zoom)
        self.selected_table_id = table.id
        self.redraw()

    def ensure_visible(self, table_id: str) -> None:
        table = self.app.project.get_table(table_id)
        if not table:
            return
        width, height = cardmetrics.card_size(table)
        x1, y1 = self._sx(table.x), self._sy(table.y)
        x2, y2 = self._sx(table.x + width), self._sy(table.y + height)
        vw, vh = self.winfo_width(), self.winfo_height()
        margin = 48
        if x1 < margin:
            self.pan_x -= (margin - x1) / self.zoom
        elif x2 > vw - margin:
            self.pan_x += (x2 - (vw - margin)) / self.zoom
        if y1 < margin:
            self.pan_y -= (margin - y1) / self.zoom
        elif y2 > vh - margin:
            self.pan_y += (y2 - (vh - margin)) / self.zoom
        self.redraw()

    def suggest_position(self, table: Table) -> tuple[float, float]:
        vw, vh = max(self.winfo_width(), 900), max(self.winfo_height(), 600)
        cx = self.pan_x + vw / (2 * self.zoom)
        cy = self.pan_y + vh / (2 * self.zoom)
        width, height = cardmetrics.card_size(table)
        base_x = cx - width / 2
        base_y = cy - height / 2
        occupied = []
        for other in self.app.project.tables:
            ow, oh = cardmetrics.card_size(other)
            occupied.append((other.x - 24, other.y - 24, other.x + ow + 24, other.y + oh + 24))

        def free(x, y):
            return not any(
                x < ox2 and x + width > ox1 and y < oy2 and y + height > oy1
                for ox1, oy1, ox2, oy2 in occupied
            )

        step = 54
        offsets = [(0, 0)]
        for ring in range(1, 9):
            for ix in range(-ring, ring + 1):
                for iy in range(-ring, ring + 1):
                    if max(abs(ix), abs(iy)) == ring:
                        offsets.append((ix * step, iy * step))
        for dx, dy in offsets:
            x = base_x + dx
            y = base_y + dy
            if free(x, y):
                return round(x / 10) * 10, round(y / 10) * 10
        return round((base_x + 8 * step) / 10) * 10, round((base_y + 8 * step) / 10) * 10
