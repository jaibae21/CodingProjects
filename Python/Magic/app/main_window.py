from __future__ import annotations
from pathlib import Path
from datetime import datetime
import sqlite3
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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
from app.scanner_controller import ScannerController

# App shell


class MainWindow(QMainWindow):
    def __init__(self, *, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.state = AppState()
        self.scanner = ScannerController(self)

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
        self.btn_capture_frame = QPushButton("Capture Frame")
        self.btn_add_dummy = QPushButton("Add Dummy Entry")
        self.btn_scan = QPushButton("Scan Card")
        self.btn_refresh = QPushButton("Refresh")

        self.chk_auto_scan = QCheckBox("Auto Scan")
        self.chk_auto_scan.setChecked(True)

        self.chk_foil = QCheckBox("Foil")

        self.cmb_condition = QComboBox()
        self.cmb_condition.addItems(["NM", "LP", "MP", "HP", "DMG"])
        self.cmb_condition.setCurrentText("NM")

        top_layout.addWidget(self.btn_new_collection)
        top_layout.addWidget(self.btn_capture_frame)
        top_layout.addWidget(self.btn_add_dummy)
        top_layout.addWidget(self.btn_scan)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.chk_auto_scan)
        top_layout.addWidget(self.chk_foil)
        top_layout.addWidget(QLabel("Condition:"))
        top_layout.addWidget(self.cmb_condition)
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
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)
        self.btn_new_collection.clicked.connect(self.on_new_collection)
        self.btn_capture_frame.clicked.connect(self.on_capture_frame)
        self.btn_add_dummy.clicked.connect(self.on_add_dummy_row)
        self.btn_scan.clicked.connect(self.on_scan_placeholder)
        self.collections_list.currentItemChanged.connect(self.on_collection_selected)

        self.chk_auto_scan.toggled.connect(self.on_auto_scan_toggled)
        self.chk_foil.toggled.connect(self.on_foil_toggled)
        self.cmb_condition.currentTextChanged.connect(self.on_condition_changed)

        self.camera_widget.latest_frame_bgr.connect(self.scanner.process_frame)
        self.scanner.status_changed.connect(self.on_scanner_status_changed)
        self.scanner.card_stable.connect(self.on_card_stable)

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

    def on_refresh_clicked(self) -> None:
        self.refresh_all()
        self.scanner.force_rescan()
        self.statusBar().showMessage("Refreshed and rescan armed", 4000)

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

    def on_capture_frame(self) -> None:
        if not hasattr(self, "camera_widget"):
            QMessageBox.warning(self, "Camera Missing", "Camera widget is not available.")
            return

        if not self.camera_widget.is_running():
            QMessageBox.information(self, "Camera Not Running", "Start the camera first.")
            return

        captures_dir = Path.cwd() / "data" / "captures"
        saved_path = self.camera_widget.save_current_frame(captures_dir)

        if saved_path is None:
            QMessageBox.warning(self, "Capture Failed", "Could not capture or save the current frame.")
            return

        self.statusBar().showMessage(f"Saved frame: {saved_path.name}", 5000)
        QMessageBox.information(self, "Frame Saved", f"Saved to:\n{saved_path}")

    def on_add_dummy_row(self) -> None:
        if not self.state.selected_collection_id:
            QMessageBox.information(self, "Select Collection", "Pick a collection first.")
            return

        dummy_card = {
            "scryfall_id": "demo-lightning-bolt-0001",
            "name": "Lightning Bolt",
            "set_code": "lea",
            "collector_number": "161",
            "rarity": "common",
            "lang": "en",
            "layout": "normal",
            "image_uri_normal": "",
            "oracle_id": "demo-oracle-lightning-bolt",
        }

        try:
            card_id, new_qty = services.add_card_to_collection_service(
                self.conn,
                collection_id=self.state.selected_collection_id,
                card=dummy_card,
                quantity=1,
                is_foil=False,
                condition="NM",
                notes="Dummy row from UI",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add dummy row:\n{e}")
            return

        self.load_entries(self.state.selected_collection_id)
        self.statusBar().showMessage(
            f"Added dummy row: Lightning Bolt (card_id={card_id}, qty={new_qty})",
            5000,
        )

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

    def on_auto_scan_toggled(self, checked: bool) -> None:
        self.state.auto_scan_enabled = checked
        self.scanner.set_enabled(checked)

    def on_foil_toggled(self, checked: bool) -> None:
        self.state.foil_enabled = checked
        self.statusBar().showMessage(f"Foil set to: {'On' if checked else 'Off'}", 3000)

    def on_condition_changed(self, value: str) -> None:
        self.state.condition = value
        self.statusBar().showMessage(f"Condition set to: {value}", 3000)

    def on_scanner_status_changed(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def on_card_stable(self, frame_bgr) -> None:
        """
        Temporary behavior:
        - show status
        - optionally save a debug image
        """
        captures_dir = Path.cwd() / "data" / "auto_captures"
        captures_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        out_path = captures_dir / f"auto_{timestamp}.jpg"

        try:
            import cv2
            cv2.imwrite(str(out_path), frame_bgr)
            self.statusBar().showMessage(
                f"Stable card detected. Saved debug frame: {out_path.name}",
                5000,
            )
        except Exception as e:
            self.statusBar().showMessage(
                f"Stable card detected, but save failed: {e}",
                5000,
            )

    # -------------------------
    # Loading data into UI
    # -------------------------

    def load_collections(self, select_collection_id: Optional[int] = None) -> None:
        self.collections_list.blockSignals(True)
        self.collections_list.clear()

        cols = services.list_collections(self.conn)
        selected_item = None

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
                    selected_item = item
                    break

        self.collections_list.blockSignals(False)

        # Manually sync state because signals were blocked during selection restore
        if selected_item is not None:
            cid = int(selected_item.data(Qt.UserRole))
            name = selected_item.text()

            self.state.selected_collection_id = cid
            self.state.selected_collection_name = name
            self.header_label.setText(f"Collection: {name}")
            self.load_entries(cid)
        else:
            self.state.selected_collection_id = None
            self.state.selected_collection_name = None
            self.header_label.setText("Select a collection")
            self.entries_table.setRowCount(0)

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