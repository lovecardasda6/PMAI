"""PMAI launcher.

Usage:
    python app.py
    python app.py path\\to\\project.pmproj
    python app.py --sample
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pmai",
        description="PMAI — sketch an app structure and translate it into an AI brief.",
    )
    parser.add_argument(
        "project",
        nargs="?",
        help="optional .pmproj or .bin project to open",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="open the built-in Billing demo project",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the version and exit",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if args.version:
        from pmai import __version__

        print(__version__)
        return 0

    from pmai.ui.main import MainWindow

    if args.smoke_test:
        window = MainWindow(sample=True)
        window.after(800, window.destroy)
        window.mainloop()
        return 0

    project_path = Path(args.project).expanduser() if args.project else None
    window = MainWindow(initial_path=project_path, sample=args.sample)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
