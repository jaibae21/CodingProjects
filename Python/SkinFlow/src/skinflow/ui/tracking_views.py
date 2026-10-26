"""Observation editing and a timeline of actual product use."""

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skinflow.models import Observation
from skinflow.tracking import CONDITIONS, REGIONS, ObservationService, care_guidance
from skinflow.ui.common import confirm, guarded
from skinflow.ui.pages import action, date_picker, readonly_table, title


class ObservationDialog(QDialog):
    def __init__(self, parent, service: ObservationService, observation: Observation | None = None):
        super().__init__(parent)
        self.service, self.observation = service, observation
        self.setWindowTitle("Edit skin observation" if observation else "Record skin observation")
        self.resize(620, 620)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.day = date_picker(observation.day if observation else None)
        self.region = QComboBox()
        self.region.setEditable(True)
        self.region.addItems(REGIONS)
        self.region.setCurrentText(observation.region if observation else "Face")
        self.condition = QComboBox()
        self.condition.addItems(CONDITIONS)
        self.condition.setCurrentText(observation.condition if observation else "Red/Irritated")
        self.severity = QSpinBox()
        self.severity.setRange(0, 5)
        self.severity.setValue(observation.severity if observation else 1)
        self.notes = QPlainTextEdit(observation.notes if observation else "")
        self.notes.setMaximumHeight(100)
        self.photo = QLineEdit(observation.photo_path if observation else "")
        self.resolved = QLineEdit(
            observation.resolved_on.isoformat() if observation and observation.resolved_on else ""
        )
        self.resolved.setPlaceholderText("YYYY-MM-DD or leave blank for unresolved")
        self.persistent = QCheckBox("Persistent / recurring concern")
        self.painful = QCheckBox("Painful")
        self.infection = QCheckBox("Concerned about possible infection")
        for checkbox, key in (
            (self.persistent, "persistent"),
            (self.painful, "painful"),
            (self.infection, "infection_concern"),
        ):
            checkbox.setChecked(bool(observation and getattr(observation, key)))
        for label, field in (
            ("Date", self.day),
            ("Region", self.region),
            ("Condition", self.condition),
            ("Severity (0–5)", self.severity),
            ("Notes", self.notes),
            ("Photo path", self.photo),
            ("Resolved on", self.resolved),
        ):
            form.addRow(label, field)
        form.addRow(self.persistent)
        form.addRow(self.painful)
        form.addRow(self.infection)
        layout.addLayout(form)
        action("Choose local photo…", self.choose_photo, layout)
        notice = QLabel(
            "A state remains active for its region until resolved or replaced by a newer "
            "state. Record Normal to clear a region. Photos stay on this computer."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def choose_photo(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Choose observation photo", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.photo.setText(path)

    @guarded
    def accept(self) -> None:
        try:
            resolved = (
                date.fromisoformat(self.resolved.text().strip())
                if self.resolved.text().strip()
                else None
            )
        except ValueError:
            raise ValueError("Resolution dates must use YYYY-MM-DD.") from None
        self.service.save(
            {
                "day": self.day.date().toPython(),
                "region": self.region.currentText(),
                "condition": self.condition.currentText(),
                "severity": self.severity.value(),
                "notes": self.notes.toPlainText(),
                "photo_path": self.photo.text(),
                "persistent": self.persistent.isChecked(),
                "painful": self.painful.isChecked(),
                "infection_concern": self.infection.isChecked(),
                "resolved_on": resolved,
            },
            self.observation.id if self.observation else None,
        )
        super().accept()


class TrackingPage(QWidget):
    def __init__(self, service: ObservationService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        title(
            layout,
            "Listen to your skin",
            "Record what you notice alongside the products you actually used.",
        )
        row = QHBoxLayout()
        action("+ Record observation", self.add, row)
        action("Edit selected", self.edit, row)
        action("Mark resolved today", self.resolve, row)
        action("Delete", self.delete, row)
        row.addStretch()
        layout.addLayout(row)
        self.table = readonly_table(
            ["Date / region", "Condition / severity", "Products used on or up to 3 days before"]
        )
        self.table.setWordWrap(True)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit())
        layout.addWidget(self.table, 2)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.details)
        self.photo = QLabel()
        layout.addWidget(self.photo)
        note = QLabel(
            "The timeline shows temporal associations, not proof of a product causing a reaction. "
            "Only marked completions appear as product use; planned steps are not treated as used."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

    @guarded
    def refresh(self) -> None:
        self.records = self.service.list()
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            completions = self.service.nearby_completions(record.day)
            used = (
                "\n".join(f"{c.day:%b %d} {c.period}: {c.label}" for c in completions)
                or "No completions recorded"
            )
            values = (
                f"{record.day}\n{record.region}",
                f"{record.condition} · {record.severity}/5"
                f"{' · resolved' if record.resolved_on else ''}",
                used,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 85)
        self.show_details()

    def selected(self) -> Observation | None:
        row = self.table.currentRow()
        return self.records[row] if 0 <= row < len(self.records) else None

    def show_details(self) -> None:
        record = self.selected()
        self.photo.clear()
        if not record:
            self.details.setText("Select an observation for notes and guidance.")
            return
        self.details.setText(f"{record.notes}\n{care_guidance(record)}")
        if record.photo_path and Path(record.photo_path).is_file():
            pixmap = QPixmap(record.photo_path)
            self.photo.setPixmap(
                pixmap.scaled(
                    220,
                    140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def add(self) -> None:
        if ObservationDialog(self, self.service).exec():
            self.refresh()

    def edit(self) -> None:
        record = self.selected()
        if record and ObservationDialog(self, self.service, record).exec():
            self.refresh()

    @guarded
    def resolve(self) -> None:
        record = self.selected()
        if record:
            self.service.resolve(record.id, date.today())
            self.refresh()

    @guarded
    def delete(self) -> None:
        record = self.selected()
        if record and confirm(
            self, "Delete observation?", "Delete this observation? Its photo file stays in place."
        ):
            self.service.delete(record.id)
            self.refresh()
