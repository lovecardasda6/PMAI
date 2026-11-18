"""Reusable widgets: rounded canvas shapes, flat buttons, dialog shell."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Callable

from .. import APP_NAME
from . import theme


def rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    *,
    fill: str = "",
    outline: str = "",
    width: float = 1.0,
    tags: tuple[str, ...] | str = (),
    steps: int = 7,
):
    """Draw an antialias-ish rounded rectangle on a canvas."""
    radius = max(0.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    if radius <= 0:
        return canvas.create_rectangle(
            x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tags
        )
    points: list[float] = []
    corners = (
        (x1 + radius, y1 + radius, 180, 270),
        (x2 - radius, y1 + radius, 270, 360),
        (x2 - radius, y2 - radius, 0, 90),
        (x1 + radius, y2 - radius, 90, 180),
    )
    for cx, cy, start, end in corners:
        for index in range(steps + 1):
            angle = math.radians(start + (end - start) * index / steps)
            points.append(cx + radius * math.cos(angle))
            points.append(cy + radius * math.sin(angle))
    return canvas.create_polygon(
        points,
        fill=fill,
        outline=outline,
        width=width,
        tags=tags,
        smooth=False,
    )


class FlatButton(tk.Button):
    """A flat button with hover states and a few visual variants."""

    VARIANTS = {
        "primary": {
            "bg": theme.ACCENT,
            "fg": "#FFFFFF",
            "hover": theme.ACCENT_HOVER,
            "press": theme.ACCENT_PRESS,
            "border": theme.ACCENT,
            "active_bg": theme.ACCENT_SOFT,
            "active_fg": theme.ACCENT_TEXT,
        },
        "tonal": {
            "bg": theme.ACCENT_SOFT,
            "fg": theme.ACCENT_TEXT,
            "hover": theme.ACCENT_SOFT_HOVER,
            "press": theme.ACCENT_SOFT_HOVER,
            "border": theme.ACCENT_SOFT,
            "active_bg": theme.ACCENT,
            "active_fg": "#FFFFFF",
        },
        "ghost": {
            "bg": theme.SURFACE,
            "fg": theme.INK_SOFT,
            "hover": "#F3F6FB",
            "press": "#EDF1F8",
            "border": theme.BORDER,
            "active_bg": theme.ACCENT,
            "active_fg": "#FFFFFF",
        },
        "subtle": {
            "bg": theme.BG,
            "fg": theme.INK_SOFT,
            "hover": "#EAEFF7",
            "press": "#E2E8F2",
            "border": theme.BG,
            "active_bg": theme.ACCENT_SOFT,
            "active_fg": theme.ACCENT_TEXT,
        },
        "danger": {
            "bg": theme.DANGER_SOFT,
            "fg": theme.DANGER,
            "hover": "#FBE0E0",
            "press": "#F7D4D4",
            "border": theme.DANGER_SOFT,
            "active_bg": theme.DANGER,
            "active_fg": "#FFFFFF",
        },
    }

    def __init__(
        self,
        master,
        text: str,
        command: Callable[[], None] | None = None,
        *,
        variant: str = "ghost",
        size: int = 10,
        weight: str = "normal",
        padx: int = 13,
        pady: int = 7,
        width: int | None = None,
        takefocus: bool = True,
        **kwargs,
    ):
        self._variant = variant if variant in self.VARIANTS else "ghost"
        self._hovering = False
        self._active = False
        colors = self.VARIANTS[self._variant]
        super().__init__(
            master,
            text=text,
            command=command,
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=colors["press"],
            activeforeground=colors["fg"],
            relief="flat",
            overrelief="flat",
            bd=0,
            highlightthickness=1 if self._variant in {"ghost", "primary"} else 0,
            highlightbackground=colors["border"],
            highlightcolor=theme.ACCENT,
            font=theme.font(size, weight),
            padx=padx,
            pady=pady,
            width=width if width is not None else 0,
            cursor="hand2",
            takefocus=takefocus,
            **kwargs,
        )
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    def _colors(self) -> dict[str, str]:
        return self.VARIANTS[self._variant]

    def _apply(self) -> None:
        colors = self._colors()
        if self._active:
            bg, fg = colors["active_bg"], colors["active_fg"]
        else:
            bg = colors["hover"] if self._hovering else colors["bg"]
            fg = colors["fg"]
        self.configure(
            bg=bg,
            fg=fg,
            activebackground=colors["press"],
            activeforeground=colors["active_fg"] if self._active else colors["fg"],
            highlightbackground=colors["border"],
        )

    def _on_enter(self, _event=None) -> None:
        self._hovering = True
        self._apply()

    def _on_leave(self, _event=None) -> None:
        self._hovering = False
        self._apply()

    def set_variant(self, variant: str) -> None:
        if variant in self.VARIANTS:
            self._variant = variant
            self._apply()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply()


class BaseDialog(tk.Toplevel):
    """Common shell for modal dialogs: header, body and footer."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        subtitle: str = "",
        *,
        width: int = 700,
        height: int = 620,
        resizable: bool = False,
    ):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.result = None
        self._width = width
        self._height = height
        self._closed = False
        self._focus_job = None
        self.title(APP_NAME)
        self.configure(bg=theme.BG)
        self.resizable(resizable, resizable)
        self.transient(parent)

        self._header = tk.Frame(self, bg=theme.SURFACE)
        self._header.pack(fill="x", side="top")
        header_inner = tk.Frame(self._header, bg=theme.SURFACE)
        header_inner.pack(fill="x", padx=26, pady=(18, 16))
        self._title_label = tk.Label(
            header_inner,
            text=title,
            bg=theme.SURFACE,
            fg=theme.INK,
            font=theme.font(15, "bold"),
            anchor="w",
        )
        self._title_label.pack(fill="x")
        self._subtitle_label = tk.Label(
            header_inner,
            text=subtitle,
            bg=theme.SURFACE,
            fg=theme.MUTED,
            font=theme.font(9),
            anchor="w",
            justify="left",
            wraplength=width - 60,
        )
        self._subtitle_label.pack(fill="x", pady=(3, 0))
        tk.Frame(self, bg=theme.BORDER, height=1).pack(fill="x")

        # Pack the footer before the expanding body so buttons are never
        # squeezed out when a dialog is tight on vertical space.
        self._footer_border = tk.Frame(self, bg=theme.BORDER, height=1)
        self._footer_border.pack(fill="x", side="bottom")
        self._footer = tk.Frame(self, bg=theme.SURFACE)
        self._footer.pack(fill="x", side="bottom")
        footer_inner = tk.Frame(self._footer, bg=theme.SURFACE)
        footer_inner.pack(fill="x", padx=24, pady=13)
        self.footer_note = tk.Label(
            footer_inner,
            text="",
            bg=theme.SURFACE,
            fg=theme.MUTED,
            font=theme.font(9),
            anchor="w",
        )
        self.footer_note.pack(side="left")
        self.footer_actions = tk.Frame(footer_inner, bg=theme.SURFACE)
        self.footer_actions.pack(side="right")

        self.body = tk.Frame(self, bg=theme.BG)
        self.body.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())

    # ---- construction helpers -----------------------------------------

    def add_footer_button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        variant: str = "ghost",
        weight: str = "normal",
    ) -> FlatButton:
        button = FlatButton(
            self.footer_actions,
            text=text,
            command=command,
            variant=variant,
            weight=weight,
            padx=16,
            pady=7,
        )
        button.pack(side="right", padx=(8, 0))
        return button

    def focus_first(self) -> None:
        self.focus_set()

    # ---- lifecycle -----------------------------------------------------

    def show(self):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(self._width, max(360, screen_w - 32))
        height = min(self._height, max(280, screen_h - 96))
        parent = self.parent
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except tk.TclError:
            px = py = 0
            pw = self.winfo_screenwidth()
            ph = self.winfo_screenheight()
        if pw <= 1:
            pw = self.winfo_screenwidth()
        if ph <= 1:
            ph = self.winfo_screenheight()
        x = px + max(0, (pw - width) // 2)
        y = py + max(0, (ph - height) // 2)
        max_x = screen_w - width - 12
        max_y = screen_h - height - 48
        x = max(12, min(x, max_x))
        y = max(12, min(y, max_y))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.grab_set()
        self._focus_job = self.after(30, self.focus_first)
        self.wait_window()
        return self.result

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._focus_job is not None:
            try:
                self.after_cancel(self._focus_job)
            except tk.TclError:
                pass
            self._focus_job = None
        try:
            if self.grab_current() is self:
                self.grab_release()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _cancel(self) -> None:
        self.result = None
        self._close()

    def _accept(self) -> None:
        self._close()


def separator(parent, *, pady: int = 12) -> tk.Frame:
    frame = tk.Frame(parent, bg=theme.BORDER, height=1)
    frame.pack(fill="x", pady=pady)
    return frame


def field_label(parent, text: str, *, bg: str = theme.BG) -> tk.Label:
    return tk.Label(
        parent,
        text=text.upper(),
        bg=bg,
        fg=theme.MUTED,
        font=theme.font(8, "bold"),
        anchor="w",
    )


def make_entry(parent, textvariable=None, *, bg=theme.SURFACE) -> tk.Entry:
    entry = tk.Entry(
        parent,
        textvariable=textvariable,
        bg=bg,
        fg=theme.INK,
        insertbackground=theme.ACCENT,
        selectbackground=theme.ACCENT_SOFT,
        selectforeground=theme.INK,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=theme.BORDER_STRONG,
        highlightcolor=theme.ACCENT,
        font=theme.font(10),
    )
    return entry


def make_text(parent, *, height: int = 4, bg=theme.SURFACE) -> tk.Text:
    return tk.Text(
        parent,
        height=height,
        wrap="word",
        bg=bg,
        fg=theme.INK,
        insertbackground=theme.ACCENT,
        selectbackground=theme.ACCENT_SOFT,
        selectforeground=theme.INK,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=theme.BORDER_STRONG,
        highlightcolor=theme.ACCENT,
        font=theme.font(10),
        padx=8,
        pady=7,
        spacing1=1,
        spacing3=1,
    )


def text_value(widget: tk.Text) -> str:
    return widget.get("1.0", "end-1c")


class InfoDialog(BaseDialog):
    """A simple formatted read-only information window."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str = "",
        *,
        width: int = 680,
        height: int = 560,
    ):
        super().__init__(
            parent,
            title,
            subtitle,
            width=width,
            height=height,
            resizable=True,
        )
        body = tk.Frame(self.body, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        wrap = tk.Frame(
            body,
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
            padx=22,
            pady=18,
            font=theme.font(10),
            spacing1=2,
            spacing3=5,
            cursor="arrow",
        )
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure(
            "h", font=theme.font(12, "bold"), foreground=theme.INK, spacing1=12, spacing3=6
        )
        self.text.tag_configure(
            "b", font=theme.font(10, "bold"), foreground=theme.INK
        )
        self.text.tag_configure(
            "mono", font=theme.font(9, family=theme.MONO_FAMILY), foreground=theme.ACCENT_TEXT
        )
        self.text.tag_configure(
            "muted", foreground=theme.MUTED
        )
        self.add_footer_button("Close", self._accept, variant="primary")
        self.text.configure(state="disabled")

    def set_rich_text(self, blocks) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for text, tag in blocks:
            self.text.insert("end", text, tag or ())
        self.text.configure(state="disabled")

    def focus_first(self) -> None:
        self.text.focus_set()
