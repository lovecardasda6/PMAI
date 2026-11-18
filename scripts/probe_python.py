"""Report Python runtime details to the PMAI bootstrap scripts.

This file is intentionally dependency-free and ASCII-only so it can run on a
bare Python installation before pip or PyInstaller exists.
"""

import base64
import os
import sys


def main():
    print("PMAI_EXE=" + base64.b64encode(os.fsencode(sys.executable)).decode("ascii"))
    print("PMAI_VERSION=%d.%d" % sys.version_info[:2])
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("PMAI_TK=missing")
    else:
        print("PMAI_TK=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
