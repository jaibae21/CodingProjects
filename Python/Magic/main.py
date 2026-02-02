from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow
from storage.db import connect, apply_migrations

def main() -> int:
    # Placing DB somewhere predictable
    data_dir = Path.home() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = data_dir / "cardds.sqlite"
    migrations_dir = Path(__file__).resolve().parent / "storage" / "migrations"

    conn = connect(db_path)
    apply_migrations(conn, migrations_dir)

    app = QApplication(sys.argv)
    win = MainWindow(conn=conn)
    win.show()

    exit_code = app.exec()

    # Clean shutdown
    try:
        conn.close()
    except Exception:
        pass

    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())