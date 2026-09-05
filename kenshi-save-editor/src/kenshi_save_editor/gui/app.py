from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from kenshi_save_editor.gui.main_window import MainWindow


def run_app(argv: list[str]) -> int:
    smoke_test = "--smoke-test" in argv
    if smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication(argv)
    app.setApplicationName("Kenshi Save Editor")
    window = MainWindow()
    window.resize(1180, 760)

    if smoke_test:
        app.processEvents()
        window.close()
        app.quit()
        return 0

    window.show()

    if len(argv) > 1:
        args = [item for item in argv[1:] if not item.startswith("--")]
        if args:
            window.open_save_folder(Path(args[0]))

    return app.exec()
