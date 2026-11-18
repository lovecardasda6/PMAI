"""Shared pytest fixtures for PMAI's Tkinter tests."""

from __future__ import annotations

import tkinter as tk

import pytest

from pmai.ui import theme
from pmai.ui.main import MainWindow


@pytest.fixture()
def root():
    window = tk.Tk()
    window.withdraw()
    theme.init_theme(window)
    theme.configure_styles(window)
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


@pytest.fixture()
def app():
    window = MainWindow()
    window.withdraw()
    if window._initial_job is not None:
        window.after_cancel(window._initial_job)
        window._initial_job = None
    window._initial_load(None, True)
    window.update()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass
