"""Temporary UI preview helper for taking screenshots of dialogs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pmai.ui.main import MainWindow


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "table"
    app = MainWindow(sample=(mode != "empty"))

    def open_dialog() -> None:
        if mode == "table":
            app.add_table()
        elif mode == "edit-table":
            app.edit_table(app.project.tables[0].id)
        elif mode == "row":
            table = app.project.get_table(app.project.tables[1].id)
            app.edit_row(table.id, table.rows[0].id)
        elif mode == "brief":
            app.show_brief()
        elif mode == "project":
            app.edit_project_details()
        elif mode == "help":
            app.show_help()
        elif mode == "link":
            app.view.set_link_mode(True)

    if mode == "link":
        app.after(700, open_dialog)
    elif mode != "empty":
        app.after(700, open_dialog)
    app.after(15000, app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
