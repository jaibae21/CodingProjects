"""Safety details and explicit review of proposed local schedule changes."""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from skinflow.safety.engine import Finding
from skinflow.safety.service import SafetyService
from skinflow.ui.common import guarded


def fill_findings(items: QListWidget, findings: list[Finding]) -> None:
    items.clear()
    for finding in findings:
        item = QListWidgetItem(finding.text())
        item.setToolTip(
            f"Rule: {finding.rule_id}\nRegions: {', '.join(finding.regions)}\n"
            + "\n".join(finding.sources)
        )
        items.addItem(item)
    if not findings:
        items.addItem("No findings from the recorded tags. Missing data can hide concerns.")


class SafetyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.findings: list[Finding] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = QLabel()
        self.summary.setObjectName("notice")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary, 1)
        details = QPushButton("Review warnings…")
        details.clicked.connect(self.show_details)
        layout.addWidget(details)

    def update_findings(self, findings: list[Finding]) -> None:
        self.findings = findings
        warnings = [f for f in findings if f.severity != "info"]
        info = len(findings) - len(warnings)
        lead = (
            warnings[0].explanation
            if warnings
            else "Warnings depend on recorded product information."
        )
        self.summary.setText(f"{len(warnings)} warnings · {info} information notes\n{lead}")

    def show_details(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Routine safety review")
        dialog.resize(830, 620)
        layout = QVBoxLayout(dialog)
        items = QListWidget()
        items.setWordWrap(True)
        items.setSpacing(12)
        fill_findings(items, self.findings)
        layout.addWidget(items)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()


class ScheduleReviewDialog(QDialog):
    def __init__(
        self,
        parent,
        schedule,
        safety: SafetyService,
        payload: dict,
        version: int,
        title: str,
        description: str,
        start: date,
        end: date | None = None,
    ):
        super().__init__(parent)
        self.schedule, self.payload, self.version = schedule, payload, version
        self.description = description
        self.setWindowTitle(title)
        self.resize(920, 680)
        layout = QVBoxLayout(self)
        notice = QLabel(
            "Review all changes and warnings. Approve saves a new schedule version. "
            "Cancel leaves your plan unchanged. Actual completions stay on their dates."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        tabs = QTabWidget()
        self.changes = QListWidget()
        self.changes.setWordWrap(True)
        self.changes.setSpacing(10)
        original, _version = schedule.snapshot()
        for group in ("weekly", "scalp", "overrides", "scalp_overrides"):
            old, new = original[group], payload[group]
            for slot in sorted(old.keys() | new.keys()):
                if old.get(slot) != new.get(slot):
                    routine = new.get(slot)
                    day, period = slot.rsplit(":", 1)
                    when = (
                        date.fromisoformat(day).strftime("%a, %b %d, %Y")
                        if "-" in day
                        else (
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        )[int(day)]
                    )
                    scope = "this date" if "overrides" in group else "every week"
                    area = "Scalp" if group.startswith("scalp") else "Face"
                    text = f"{when} · {period} · {area} · {scope}\n"
                    if routine and routine.get("shower"):
                        text += "Shower session\n"
                    text += (
                        "Resume recurring routine"
                        if routine is None
                        else "\n".join(
                            f"{i}. {s['label']}" for i, s in enumerate(routine["steps"], 1)
                        )
                        or "Empty routine"
                    )
                    item = QListWidgetItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, (group, slot))
                    self.changes.addItem(item)
        if original["monthly"] != payload["monthly"]:
            self.changes.addItem("Monthly rules replaced with the selected template's rules.")
        if original["monthly_decisions"] != payload["monthly_decisions"]:
            for key, decision in payload["monthly_decisions"].items():
                if original["monthly_decisions"].get(key) != decision:
                    rule_id, occurrence = key.rsplit(":", 1)
                    rule_name = next(
                        (r["name"] for r in payload["monthly"] if r["id"] == rule_id), "Treatment"
                    )
                    self.changes.addItem(f"{rule_name} · {occurrence}: {decision['status']}")
        tabs.addTab(self.changes, "Proposed changes")
        warnings = QListWidget()
        warnings.setWordWrap(True)
        warnings.setSpacing(12)
        if end and (end - start).days > 62:
            findings = safety.review(start, payload=payload) + safety.review(end, payload=payload)
        else:
            findings = safety.review(start, end, payload)
        fill_findings(warnings, findings)
        tabs.addTab(warnings, "Warnings and evidence")
        layout.addWidget(tabs)
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        box.button(QDialogButtonBox.StandardButton.Save).setText("Approve changes")
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    @guarded
    def accept(self) -> None:
        self.schedule.apply_preview(self.payload, self.version, self.description)
        super().accept()
