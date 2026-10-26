"""Desktop entry point. Inventory, schedules, safety, and tracking work offline."""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from skinflow.database import Database, default_data_dir
from skinflow.seed import seed
from skinflow.ui.window import MainWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SkinFlow local desktop routine manager")
    parser.add_argument("--data-dir", type=Path, help="Store the SQLite database in this folder")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("SkinFlow")
    app.setOrganizationName("SkinFlow")
    app.setStyle("Fusion")
    database = None
    try:
        data_dir = (args.data_dir or default_data_dir()).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            data_dir / "skinflow.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        database = Database(data_dir / "skinflow.db")
        database.migrate()
        seed(database)
        window = MainWindow(database)
        window.show()
        if args.smoke_test:
            QTimer.singleShot(500, app.quit)
        return app.exec()
    except Exception:
        logging.getLogger(__name__).exception("Startup failed")
        if not args.smoke_test:
            QMessageBox.critical(
                None,
                "SkinFlow could not start",
                "Unable to open the local database or application. "
                "Check folder permissions and skinflow.log in the data folder.",
            )
        return 1
    finally:
        if database:
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
