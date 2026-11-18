"""Shared card geometry used by the canvas and the auto-layout engine."""

from __future__ import annotations

import textwrap

from .models import Table

CARD_W = 460
PAD = 18
HEADER_H = 55
COL_H = 31
ROW_H = 37
EMPTY_H = 50
NOTE_TOP = 14
NOTE_TITLE_H = 20
NOTE_LINE_H = 18
BOTTOM_PAD = 14
MAX_VISIBLE_ROWS = 14
MAX_NOTE_LINES = 6

NAME_X = PAD
TYPE_X = 198
NOTES_X = 322
RIGHT_X = CARD_W - PAD
NAME_W = TYPE_X - NAME_X - 12
TYPE_W = NOTES_X - TYPE_X - 12
NOTES_W = RIGHT_X - NOTES_X


def visible_rows(table: Table):
    return table.rows[:MAX_VISIBLE_ROWS]


def note_lines(notes: str) -> list[str]:
    text = str(notes or "").strip()
    if not text:
        return []
    chars = max(20, int((CARD_W - PAD * 2) / 6.1))
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            paragraph,
            width=chars,
            break_long_words=True,
            replace_whitespace=False,
        ) or [""]
        lines.extend(wrapped)
    if len(lines) > MAX_NOTE_LINES:
        kept = lines[:MAX_NOTE_LINES]
        kept[-1] = kept[-1].rstrip(" .") + "…"
        lines = kept
    return lines


def notes_block_height(table: Table) -> int:
    lines = note_lines(table.notes)
    if not lines:
        return 0
    return NOTE_TOP + NOTE_TITLE_H + len(lines) * NOTE_LINE_H + 10


def card_height(table: Table) -> int:
    height = HEADER_H + COL_H
    visible = visible_rows(table)
    if visible:
        height += len(visible) * ROW_H
        if len(table.rows) > MAX_VISIBLE_ROWS:
            height += 28
    else:
        height += EMPTY_H
    height += notes_block_height(table)
    height += BOTTOM_PAD
    return height


def card_size(table: Table) -> tuple[int, int]:
    return CARD_W, card_height(table)
