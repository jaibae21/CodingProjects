from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.state import AppState
from app import services
from storage.db import UniqueConstraintError

from app.camera_widget import CameraWidget

# App shell


class MainWindow(QMainWindow):
    def __init__(self, *, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.state = AppState()

        self.setWindowTitle("Magic Card Scanner")
        self.resize(1100, 650)

        # ----- Root layout -----
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)

        # Top bar
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_new_collection = QPushButton("New Collection")
        self.btn_scan = QPushButton("Scan Card")
        self.btn_refresh = QPushButton("Refresh")

        top_layout.addWidget(self.btn_new_collection)
        top_layout.addWidget(self.btn_scan)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addStretch(1)

        root_layout.addWidget(top_bar)

        # Split view: collections (left) | entries (right)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(QLabel("Collections"))
        self.collections_list = QListWidget()
        left_layout.addWidget(self.collections_list)

        splitter.addWidget(left)

        # Right panel
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.header_label = QLabel("Select a collection")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        right_layout.addWidget(self.header_label)

        # Camera Preview
        self.camera_widget = CameraWidget(max_devices=4)
        right_layout.addWidget(self.camera_widget)

        # Entries table
        self.entries_table = QTableWidget(0, 8)
        self.entries_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Set",
                "#",
                "Qty",
                "Foil",
                "Condition",
                "Notes",
                "Added",
            ]
        )
        self.entries_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.entries_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.entries_table.horizontalHeader().setStretchLastSection(True)

        right_layout.addWidget(self.entries_table)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")

        # ----- Signals -----
        self.btn_refresh.clicked.connect(self.refresh_all)
        self.btn_new_collection.clicked.connect(self.on_new_collection)
        self.btn_scan.clicked.connect(self.on_scan_placeholder)
        self.collections_list.currentItemChanged.connect(self.on_collection_selected)

        # Initial load
        self.refresh_all()

    # -------------------------
    # UI actions
    # -------------------------

    def refresh_all(self) -> None:
        self.load_collections()
        # If current selection still exists, keep it; otherwise clear
        if self.state.selected_collection_id is not None:
            self.load_entries(self.state.selected_collection_id)
        else:
            self.entries_table.setRowCount(0)
            self.header_label.setText("Select a collection")
        self.statusBar().showMessage("Refreshed")

    def on_new_collection(self) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Create Collection")
        dlg.setText("Enter a new collection name:")
        dlg.setIcon(QMessageBox.Question)

        input_box = QLineEdit(dlg)
        input_box.setPlaceholderText("e.g., Commander Decks, Trade Binder, etc.")
        input_box.setMinimumWidth(350)

        # Hacky-but-simple layout injection for QMessageBox
        layout = dlg.layout()
        layout.addWidget(input_box, 1, 1, 1, layout.columnCount(), Qt.AlignLeft)

        dlg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = dlg.exec()

        if ret != QMessageBox.Ok:
            return

        name = input_box.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Collection name cannot be empty.")
            return

        try:
            new_id = services.create_collection_service(self.conn, name)
        except UniqueConstraintError:
            QMessageBox.warning(self, "Already Exists", f"'{name}' already exists.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create collection:\n{e}")
            return

        self.statusBar().showMessage(f"Created collection: {name}")
        self.load_collections(select_collection_id=new_id)

    def on_scan_placeholder(self) -> None:
        if not self.state.selected_collection_id:
            QMessageBox.information(self, "Select Collection", "Pick a collection first.")
            return

        # Placeholder: later this will open camera, run detection/OCR, call Scryfall, etc.
        QMessageBox.information(
            self,
            "Scan Card (placeholder)",
            "Scanner pipeline not hooked up yet.\n\nNext step: camera → identify → Scryfall → add_card_to_collection().",
        )

    def on_collection_selected(self, current: Optional[QListWidgetItem], _prev: Optional[QListWidgetItem]) -> None:
        if current is None:
            self.state.selected_collection_id = None
            self.state.selected_collection_name = None
            self.entries_table.setRowCount(0)
            self.header_label.setText("Select a collection")
            return

        cid = current.data(Qt.UserRole)
        name = current.text()

        self.state.selected_collection_id = int(cid)
        self.state.selected_collection_name = name

        self.header_label.setText(f"Collection: {name}")
        self.load_entries(int(cid))

    # -------------------------
    # Loading data into UI
    # -------------------------

    def load_collections(self, select_collection_id: Optional[int] = None) -> None:
        self.collections_list.blockSignals(True)
        self.collections_list.clear()

        cols = services.list_collections(self.conn)
        for c in cols:
            item = QListWidgetItem(c["name"])
            item.setData(Qt.UserRole, c["id"])
            self.collections_list.addItem(item)

        # restore selection
        target_id = select_collection_id or self.state.selected_collection_id
        if target_id is not None:
            for i in range(self.collections_list.count()):
                item = self.collections_list.item(i)
                if int(item.data(Qt.UserRole)) == int(target_id):
                    self.collections_list.setCurrentItem(item)
                    break

        self.collections_list.blockSignals(False)

    def load_entries(self, collection_id: int) -> None:
        rows = services.list_collection_entries(self.conn, collection_id)

        self.entries_table.setRowCount(0)
        self.entries_table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self._set_cell(r, 0, row.get("card_name", ""))
            self._set_cell(r, 1, row.get("set_code", ""))
            self._set_cell(r, 2, row.get("collector_number", ""))
            self._set_cell(r, 3, str(row.get("quantity", "")))
            self._set_cell(r, 4, "Yes" if row.get("is_foil") else "No")
            self._set_cell(r, 5, row.get("condition") or "")
            self._set_cell(r, 6, row.get("notes") or "")
            self._set_cell(r, 7, row.get("added_at") or "")

        self.entries_table.resizeColumnsToContents()

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.entries_table.setItem(row, col, item)


    def closeEvent(self, event) -> None:
        try:
            if hasattr(self, "camera_widget"):
                self.camera_widget.stop()
        except Exception:
            pass
        super().closeEvent(event)