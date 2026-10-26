from copy import deepcopy
from datetime import date
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from skinflow.models import Product
from skinflow.safety.tags import TAGS
from skinflow.services import (
    CATEGORIES,
    PERIOD_LABELS,
    PERIODS,
    STATUSES,
    InventoryService,
    empty_routine,
    new_step,
)
from skinflow.ui.common import guarded

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def buttons(dialog: QDialog, layout: QVBoxLayout) -> QDialogButtonBox:
    box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    layout.addWidget(box)
    return box


class ProductDialog(QDialog):
    def __init__(self, parent, inventory: InventoryService, product: Product | None = None):
        super().__init__(parent)
        self.inventory, self.product = inventory, product
        self.setWindowTitle("Edit product" if product else "Add product")
        self.resize(610, 740)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        self.fields: dict[str, QWidget] = {}
        for key, label in (("brand", "Brand"), ("name", "Product name *")):
            self._text(form, key, label)
        for key, label, choices in (
            ("category", "Category", CATEGORIES),
            ("status", "Status", STATUSES),
            ("suitability", "When to use", ("AM/PM", "AM", "PM")),
        ):
            field = QComboBox()
            field.addItems(choices)
            if product:
                field.setCurrentText(getattr(product, key))
            self.fields[key] = field
            form.addRow(label, field)
        for key, label in (
            ("ingredients", "Full ingredient list"),
            ("actives", "Important actives"),
            ("purpose", "Purpose"),
            ("instructions", "Instructions"),
            ("notes", "Personal notes"),
        ):
            field = QPlainTextEdit()
            field.setMaximumHeight(76)
            field.setPlaceholderText("Unknown / unverified" if key != "notes" else "Optional")
            if product:
                field.setPlainText(getattr(product, key))
            self.fields[key] = field
            form.addRow(label, field)
        self.verified = QCheckBox("I verified the full ingredient list against the label")
        self.verified.setChecked(bool(product and product.ingredients_verified))
        form.addRow(self.verified)
        tag_notice = QLabel(
            "Safety tags are explicit records, separate from full ingredient verification."
        )
        tag_notice.setWordWrap(True)
        form.addRow(tag_notice)
        self.tags = {}
        for key, label in TAGS.items():
            row = QHBoxLayout()
            checked = QCheckBox(label)
            source = QComboBox()
            source.addItem("User reported", "user_reported")
            source.addItem("Label verified", "label_verified")
            note = QLineEdit()
            note.setPlaceholderText("Evidence / label notes")
            evidence = (product.safety_tags or {}).get(key) if product else None
            if evidence:
                checked.setChecked(True)
                source.setCurrentIndex(source.findData(evidence["source"]))
                note.setText(evidence.get("note", ""))
            for field in (checked, source, note):
                row.addWidget(field)
            self.tags[key] = (checked, source, note)
            form.addRow(row)
        self._text(form, "frequency", "Recommended frequency")
        for key, label in (("opened_on", "Opened date"), ("expires_on", "Expiration date")):
            field = QLineEdit()
            field.setPlaceholderText("YYYY-MM-DD or leave blank")
            if product and getattr(product, key):
                field.setText(getattr(product, key).isoformat())
            self.fields[key] = field
            form.addRow(label, field)
        self._text(form, "expiration_notes", "Expiration / PAO notes")
        self._text(form, "image_path", "Product image path")
        browse = QPushButton("Choose image…")
        browse.clicked.connect(self.choose_image)
        form.addRow("", browse)
        self.preview = QLabel()
        form.addRow("", self.preview)
        self.fields["image_path"].textChanged.connect(self.preview_image)
        self.preview_image()
        if product:
            form.addRow("Added", QLabel(product.date_added.isoformat()))
        scroll.setWidget(body)
        layout.addWidget(scroll)
        buttons(self, layout)

    def _text(self, form: QFormLayout, key: str, label: str) -> None:
        field = QLineEdit(getattr(self.product, key) if self.product else "")
        self.fields[key] = field
        form.addRow(label, field)

    def choose_image(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.fields["image_path"].setText(path)

    def preview_image(self) -> None:
        path = self.fields["image_path"].text().strip()
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        self.preview.setPixmap(
            pixmap.scaled(
                180,
                110,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    @guarded
    def accept(self) -> None:
        data = {}
        for key, field in self.fields.items():
            if isinstance(field, QComboBox):
                value = field.currentText()
            elif isinstance(field, QPlainTextEdit):
                value = field.toPlainText()
            else:
                value = field.text()
            if key in ("opened_on", "expires_on"):
                try:
                    value = date.fromisoformat(value.strip()) if value.strip() else None
                except ValueError:
                    raise ValueError("Dates must use YYYY-MM-DD.") from None
            data[key] = value
        data["ingredients_verified"] = self.verified.isChecked()
        data["safety_tags"] = {
            key: {"source": source.currentData(), "note": note.text().strip()}
            for key, (checked, source, note) in self.tags.items()
            if checked.isChecked()
        }
        if data["ingredients_verified"] and not data["ingredients"].strip():
            raise ValueError("Enter the ingredient list before marking it verified.")
        self.inventory.save(data, self.product.id if self.product else None)
        super().accept()


class StepDialog(QDialog):
    def __init__(self, parent, inventory: InventoryService, step: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Routine step")
        self.resize(700, 620)
        self.original = step
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.product = QComboBox()
        self.product.addItem("Reminder / no product", None)
        for product in inventory.list():
            self.product.addItem(f"{product.label} [{product.status}]", product.id)
        if step and step["product_id"] is not None:
            index = self.product.findData(step["product_id"])
            if index < 0:
                self.product.addItem(f"{step['label']} [deleted]", step["product_id"])
                index = self.product.count() - 1
            self.product.setCurrentIndex(index)
        self.label = QLineEdit(step["label"] if step else "")
        self.product.currentIndexChanged.connect(self.set_product_label)
        self.optional = QCheckBox("Optional / only if tolerated")
        self.review = QCheckBox("Caution / review reminder")
        if step:
            self.optional.setChecked(step["optional"])
            self.review.setChecked(step["review"])
        form.addRow("Product", self.product)
        form.addRow("Step label", self.label)
        form.addRow(self.optional)
        form.addRow(self.review)
        self.region = QComboBox()
        self.region.setEditable(True)
        self.region.addItems(("Face", "Eyebrows", "Nose", "Scalp", "Body"))
        self.region.setCurrentText(step.get("region", "Face") if step else "Face")
        self.instructions = QPlainTextEdit(step.get("instructions", "") if step else "")
        self.instructions.setMaximumHeight(70)
        self.skip_conditions = QLineEdit(step.get("skip_conditions", "") if step else "")
        self.frequency = QLineEdit(step.get("frequency", "") if step else "")
        self.substitutions = QListWidget()
        self.substitutions.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.substitutions.setMaximumHeight(100)
        for product in inventory.list():
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(product.label)
            item.setData(Qt.ItemDataRole.UserRole, product.id)
            self.substitutions.addItem(item)
            item.setSelected(bool(step and product.id in step.get("substitutions", [])))
        form.addRow("Application region", self.region)
        form.addRow("Product directions", self.instructions)
        form.addRow("Skip conditions", self.skip_conditions)
        form.addRow("Frequency notes", self.frequency)
        form.addRow("Substitution options", self.substitutions)
        layout.addLayout(form)
        buttons(self, layout)
        self.result_step = None

    def set_product_label(self) -> None:
        if self.product.currentData() is not None:
            self.label.setText(self.product.currentText().rsplit(" [", 1)[0])

    @guarded
    def accept(self) -> None:
        if not self.label.text().strip():
            raise ValueError("Enter a step label.")
        self.result_step = new_step(
            self.label.text().strip(),
            self.product.currentData(),
            optional=self.optional.isChecked(),
            review=self.review.isChecked(),
        )
        if self.original:
            self.result_step["id"] = self.original["id"]
        self.result_step.update(
            region=self.region.currentText().strip() or "Face",
            instructions=self.instructions.toPlainText(),
            skip_conditions=self.skip_conditions.text(),
            frequency=self.frequency.text(),
            substitutions=[
                i.data(Qt.ItemDataRole.UserRole) for i in self.substitutions.selectedItems()
            ],
        )
        super().accept()


class RoutineDialog(QDialog):
    def __init__(self, parent, inventory: InventoryService, routine: dict, title: str):
        super().__init__(parent)
        self.inventory = inventory
        self.result_routine = deepcopy(routine)
        self.result_routine.pop("overridden", None)
        self.setWindowTitle(title)
        self.resize(720, 460)
        layout = QVBoxLayout(self)
        label = QLabel("Steps are applied from top to bottom. Use ↑ / ↓ to change their order.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.shower = QCheckBox("Shower routine")
        self.shower.setChecked(routine["shower"])
        layout.addWidget(self.shower)
        self.steps = QListWidget()
        self.steps.itemDoubleClicked.connect(lambda _item: self.edit_step())
        layout.addWidget(self.steps)
        actions = QHBoxLayout()
        for text, callback in (
            ("Add", self.add_step),
            ("Edit", self.edit_step),
            ("Remove", self.remove_step),
            ("↑", lambda: self.reorder(-1)),
            ("↓", lambda: self.reorder(1)),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        buttons(self, layout)
        self.refresh()

    def refresh(self, selected: int = 0) -> None:
        self.steps.clear()
        for i, step in enumerate(self.result_routine["steps"], 1):
            suffix = (" • optional" if step["optional"] else "") + (
                " • REVIEW" if step["review"] else ""
            )
            self.steps.addItem(f"{i}. {step['label']}{suffix}")
        self.steps.setCurrentRow(selected)

    def add_step(self) -> None:
        dialog = StepDialog(self, self.inventory)
        if dialog.exec():
            self.result_routine["steps"].append(dialog.result_step)
            self.refresh(len(self.result_routine["steps"]) - 1)

    def edit_step(self) -> None:
        index = self.steps.currentRow()
        if index >= 0:
            dialog = StepDialog(self, self.inventory, self.result_routine["steps"][index])
            if dialog.exec():
                self.result_routine["steps"][index] = dialog.result_step
                self.refresh(index)

    def remove_step(self) -> None:
        index = self.steps.currentRow()
        if index >= 0:
            self.result_routine["steps"].pop(index)
            self.refresh(max(0, index - 1))

    def reorder(self, offset: int) -> None:
        index = self.steps.currentRow()
        target = index + offset
        steps = self.result_routine["steps"]
        if index >= 0 and 0 <= target < len(steps):
            steps[index], steps[target] = steps[target], steps[index]
            self.refresh(target)

    def accept(self) -> None:
        self.result_routine["shower"] = self.shower.isChecked()
        super().accept()


class MonthlyRuleDialog(QDialog):
    def __init__(self, parent, inventory: InventoryService, rule: dict | None = None):
        super().__init__(parent)
        self.inventory = inventory
        self.rule = (
            deepcopy(rule)
            if rule
            else {
                "id": uuid4().hex,
                "name": "Monthly treatment",
                "ordinal": 1,
                "weekday": 5,
                "period": "Night",
                "enabled": True,
                "routine": empty_routine(),
            }
        )
        self.setWindowTitle("Monthly recurring treatment")
        self.resize(480, 320)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(self.rule["name"])
        self.ordinal = QComboBox()
        self.ordinal.addItems(("First", "Second", "Third", "Fourth", "Fifth (when present)"))
        self.ordinal.setCurrentIndex(self.rule["ordinal"] - 1)
        self.weekday = QComboBox()
        self.weekday.addItems(DAYS)
        self.weekday.setCurrentIndex(self.rule["weekday"])
        self.period = QComboBox()
        for key, label in zip(PERIODS, PERIOD_LABELS):
            self.period.addItem(label, key)
        self.period.setCurrentIndex(self.period.findData(self.rule["period"]))
        self.requires_review = QCheckBox("Require review for each occurrence")
        self.requires_review.setChecked(self.rule.get("requires_review", False))
        self.mode = QComboBox()
        self.mode.addItems(("Append to routine", "Replace routine"))
        self.mode.setCurrentIndex(1 if self.rule.get("mode") == "replace" else 0)
        self.before = QComboBox()
        self.after = QComboBox()
        for field, key in ((self.before, "recovery_before"), (self.after, "recovery_after")):
            field.addItems([str(i) for i in range(8)])
            field.setCurrentIndex(self.rule.get(key, 0))
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(self.rule["enabled"])
        for label, field in (
            ("Name", self.name),
            ("Occurrence", self.ordinal),
            ("Weekday", self.weekday),
            ("Period", self.period),
        ):
            form.addRow(label, field)
        form.addRow(self.enabled)
        form.addRow(self.requires_review)
        form.addRow("When approved", self.mode)
        form.addRow("Recovery days before", self.before)
        form.addRow("Recovery days after", self.after)
        layout.addLayout(form)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        edit = QPushButton("Edit treatment steps…")
        edit.clicked.connect(self.edit_steps)
        layout.addWidget(edit)
        buttons(self, layout)
        self.update_summary()

    def update_summary(self) -> None:
        self.summary.setText(f"{len(self.rule['routine']['steps'])} treatment steps.")

    def edit_steps(self) -> None:
        dialog = RoutineDialog(
            self, self.inventory, self.rule["routine"], "Monthly treatment steps"
        )
        if dialog.exec():
            self.rule["routine"] = dialog.result_routine
            self.update_summary()

    @guarded
    def accept(self) -> None:
        if not self.name.text().strip():
            raise ValueError("Enter a name for this treatment.")
        self.rule.update(
            name=self.name.text().strip(),
            ordinal=self.ordinal.currentIndex() + 1,
            weekday=self.weekday.currentIndex(),
            period=self.period.currentData(),
            enabled=self.enabled.isChecked(),
            requires_review=self.requires_review.isChecked(),
            mode="replace" if self.mode.currentIndex() == 1 else "append",
            recovery_before=self.before.currentIndex(),
            recovery_after=self.after.currentIndex(),
        )
        super().accept()


class MonthlyDialog(QDialog):
    def __init__(self, parent, inventory: InventoryService, schedule):
        super().__init__(parent)
        self.inventory, self.schedule = inventory, schedule
        payload, self.version = schedule.snapshot()
        self.rules = payload["monthly"]
        self.setWindowTitle("Monthly treatments")
        self.resize(650, 390)
        layout = QVBoxLayout(self)
        notice = QLabel(
            "Monthly rules can append or replace a session. Treatments marked for review "
            "remain reminders until an occurrence is explicitly approved in the calendar."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.items = QListWidget()
        self.items.itemDoubleClicked.connect(lambda _item: self.edit())
        layout.addWidget(self.items)
        actions = QHBoxLayout()
        for text, callback in (("Add", self.add), ("Edit", self.edit), ("Remove", self.remove)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        buttons(self, layout)
        self.refresh()

    def refresh(self) -> None:
        self.items.clear()
        for rule in self.rules:
            self.items.addItem(
                f"{rule['name']} • {rule['ordinal']} {DAYS[rule['weekday']]} "
                f"{rule['period']} • {'enabled' if rule['enabled'] else 'disabled'}"
            )

    def add(self) -> None:
        dialog = MonthlyRuleDialog(self, self.inventory)
        if dialog.exec():
            self.rules.append(dialog.rule)
            self.refresh()

    def edit(self) -> None:
        index = self.items.currentRow()
        if index >= 0:
            dialog = MonthlyRuleDialog(self, self.inventory, self.rules[index])
            if dialog.exec():
                self.rules[index] = dialog.rule
                self.refresh()

    def remove(self) -> None:
        index = self.items.currentRow()
        if index >= 0:
            self.rules.pop(index)
            self.refresh()

    @guarded
    def accept(self) -> None:
        self.schedule.save_monthly(self.rules, self.version)
        super().accept()
