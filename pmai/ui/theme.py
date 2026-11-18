"""Visual theme for PMAI."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ---- palette ------------------------------------------------------------

BG = "#F4F6FB"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFD"
INK = "#172033"
INK_SOFT = "#3E4A5F"
MUTED = "#74809A"
FAINT = "#A2ADBF"
BORDER = "#E1E7F0"
BORDER_STRONG = "#CBD5E4"
GRID_DOT = "#D6E0EE"

ACCENT = "#4F46E5"
ACCENT_HOVER = "#4338CA"
ACCENT_PRESS = "#3730A3"
ACCENT_SOFT = "#EEF0FF"
ACCENT_SOFT_HOVER = "#E2E5FF"
ACCENT_TEXT = "#3730A3"

MENU_FG = "#A9620B"
MENU_BG = "#FFF3E0"
MENU_LINE = "#E7A845"
FIELDS_FG = "#1D4ED8"
FIELDS_BG = "#E8F0FF"
FIELDS_LINE = "#6492F5"
COMPONENTS_FG = "#0F766E"
COMPONENTS_BG = "#E6FFFA"
COMPONENTS_LINE = "#2DD4BF"

LINK_COLOR = "#7286F2"
LINK_SELECTED = "#4338CA"
NOTE_TEXT = "#5E6B80"

SUCCESS = "#0E9F6E"
SUCCESS_SOFT = "#E9FBF3"
DANGER = "#D14343"
DANGER_SOFT = "#FDECEC"
WARNING = "#B46A0B"

TYPE_COLORS: dict[str, tuple[str, str]] = {
    "Menu": (MENU_FG, MENU_BG),
    "Text": ("#4B5A70", "#F1F4F8"),
    "Long Text": ("#4B5A70", "#F1F4F8"),
    "Number": ("#047857", "#ECFDF5"),
    "Integer": ("#047857", "#ECFDF5"),
    "Decimal": ("#047857", "#ECFDF5"),
    "Currency": ("#047857", "#ECFDF5"),
    "Boolean": ("#7C3AED", "#F5F3FF"),
    "Date": ("#C2410C", "#FFF5EB"),
    "Time": ("#C2410C", "#FFF5EB"),
    "DateTime": ("#C2410C", "#FFF5EB"),
    "Email": ("#0369A1", "#F0F9FF"),
    "Phone": ("#0369A1", "#F0F9FF"),
    "URL": ("#0369A1", "#F0F9FF"),
    "Select": ("#BE185D", "#FDF2F8"),
    "Multi Select": ("#BE185D", "#FDF2F8"),
    "Enum": ("#7E22CE", "#FAF5FF"),
    "DropDown": ("#0369A1", "#F0F9FF"),
    "Auto ID": ("#4338CA", "#EEF2FF"),
    "Reference": ("#1D4ED8", "#EFF6FF"),
    "File": ("#0F766E", "#F0FDFA"),
    "Image": ("#0F766E", "#F0FDFA"),
    "Password": ("#BE123C", "#FFF1F2"),
    "JSON": ("#52525B", "#F4F4F5"),
    "Formula": ("#7E22CE", "#FAF5FF"),
    "Button": ("#4338CA", "#EEF2FF"),
    "TextBox": ("#0E7490", "#ECFEFF"),
    "Text Area": ("#155E75", "#E0F2FE"),
    "Table": ("#0F766E", "#E6FFFA"),
    "Tabs": ("#BE185D", "#FDF2F8"),
    "H1": ("#6D28D9", "#F5F3FF"),
    "H2": ("#7C3AED", "#F5F3FF"),
    "H3": ("#8B5CF6", "#FAF5FF"),
    "H4": ("#9333EA", "#FAF5FF"),
    "H5": ("#A855F7", "#FDF4FF"),
    "H6": ("#C026D3", "#FDF4FF"),
}
DEFAULT_TYPE_COLORS = ("#5B6880", "#F1F4F8")

UI_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"


def init_theme(root: tk.Misc) -> None:
    global UI_FAMILY, MONO_FAMILY
    families = set(tkfont.families(root))
    for candidate in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue"):
        if candidate in families:
            UI_FAMILY = candidate
            break
    for candidate in ("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New"):
        if candidate in families:
            MONO_FAMILY = candidate
            break


def font(size: int = 10, weight: str = "normal", family: str | None = None):
    return (family or UI_FAMILY, size, weight)


def px_font(size_px: float, weight: str = "normal", family: str | None = None):
    return (family or UI_FAMILY, -max(7, int(round(size_px))), weight)


def type_colors(type_name: str) -> tuple[str, str]:
    return TYPE_COLORS.get(type_name, DEFAULT_TYPE_COLORS)


def kind_colors(kind: str) -> tuple[str, str]:
    if kind == "menu":
        return MENU_FG, MENU_BG
    if kind == "components":
        return COMPONENTS_FG, COMPONENTS_BG
    return FIELDS_FG, FIELDS_BG


def configure_styles(root: tk.Misc) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE,
        foreground=INK,
        bordercolor=BORDER_STRONG,
        lightcolor=BORDER_STRONG,
        darkcolor=BORDER_STRONG,
        arrowcolor=MUTED,
        padding=6,
        arrowsize=14,
        font=font(10),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", SURFACE), ("disabled", SURFACE_ALT)],
        selectbackground=[("readonly", SURFACE)],
        selectforeground=[("readonly", INK)],
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    style.configure(
        "Editor.Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=INK,
        rowheight=31,
        borderwidth=0,
        font=font(10),
    )
    style.map(
        "Editor.Treeview",
        background=[("selected", ACCENT_SOFT)],
        foreground=[("selected", INK)],
    )
    style.configure(
        "Editor.Treeview.Heading",
        background=SURFACE_ALT,
        foreground=MUTED,
        relief="flat",
        borderwidth=0,
        padding=(8, 8),
        font=font(9, "bold"),
    )
    style.map(
        "Editor.Treeview.Heading",
        background=[("active", SURFACE_ALT)],
    )

    style.configure(
        "Vertical.TScrollbar",
        gripcount=0,
        background="#C7D1E1",
        darkcolor="#C7D1E1",
        lightcolor="#C7D1E1",
        troughcolor=SURFACE_ALT,
        bordercolor=SURFACE_ALT,
        arrowcolor=MUTED,
        arrowsize=12,
        width=12,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", BORDER_STRONG)],
    )
    style.configure(
        "Horizontal.TScrollbar",
        gripcount=0,
        background="#C7D1E1",
        darkcolor="#C7D1E1",
        lightcolor="#C7D1E1",
        troughcolor=SURFACE_ALT,
        bordercolor=SURFACE_ALT,
        arrowcolor=MUTED,
        arrowsize=12,
        width=12,
    )

    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", INK)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", INK)
    root.option_add("*TCombobox*Listbox.font", font(10))
