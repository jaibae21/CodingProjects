from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skinflow.safety.service import SafetyService
from skinflow.services import (
    CATEGORIES,
    PERIOD_LABELS,
    PERIODS,
    STATUSES,
    InventoryService,
    ScheduleService,
    SettingsService,
)
from skinflow.ui.common import confirm, guarded
from skinflow.ui.dialogs import MonthlyDialog, ProductDialog, RoutineDialog
from skinflow.ui.safety_views import SafetyPanel, ScheduleReviewDialog


def title(layout: QVBoxLayout, heading: str, description: str) -> None:
    label = QLabel(heading)
    label.setObjectName("pageTitle")
    layout.addWidget(label)
    subtitle = QLabel(description)
    subtitle.setWordWrap(True)
    subtitle.setObjectName("subtitle")
    layout.addWidget(subtitle)


def action(text: str, callback, layout) -> QPushButton:
    button = QPushButton(text)
    button.clicked.connect(lambda _checked=False: callback())
    layout.addWidget(button)
    return button


def date_picker(day: date | None = None) -> QDateEdit:
    picker = QDateEdit(QDate(day or date.today()))
    picker.setCalendarPopup(True)
    picker.setDisplayFormat("ddd, MMM d, yyyy")
    return picker


def readonly_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


class DashboardPage(QWidget):
    def __init__(
        self, inventory: InventoryService, schedule: ScheduleService, safety: SafetyService
    ):
        super().__init__()
        self.inventory, self.schedule = inventory, schedule
        self.safety = safety
        layout = QVBoxLayout(self)
        title(layout, "Your daily ritual", "An editable plan, one step at a time.")
        row = QHBoxLayout()
        self.day = date_picker()
        self.period = QComboBox()
        for key, label in zip(PERIODS, PERIOD_LABELS):
            self.period.addItem(label, key)
        hour = datetime.now().hour
        self.period.setCurrentIndex(0 if hour < 12 else 1)
        self.area = QComboBox()
        self.area.addItems(("Face", "Scalp"))
        row.addWidget(self.day)
        row.addWidget(self.period)
        row.addWidget(self.area)
        row.addStretch()
        action("Today", self.today, row)
        layout.addLayout(row)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.warnings = SafetyPanel()
        layout.addWidget(self.warnings)
        self.steps = QListWidget()
        self.steps.setSpacing(6)
        self.steps.itemChanged.connect(self.mark)
        layout.addWidget(self.steps, 2)
        self.next_label = QLabel()
        self.next_label.setWordWrap(True)
        layout.addWidget(self.next_label)
        layout.addWidget(QLabel("Recent completions • recorded separately from your plan"))
        self.history = readonly_table(["Date", "Session", "Completed step"])
        layout.addWidget(self.history, 1)
        self.day.dateChanged.connect(lambda _date: self.refresh())
        self.period.currentTextChanged.connect(lambda _text: self.refresh())
        self.area.currentTextChanged.connect(lambda _text: self.refresh())

    def today(self) -> None:
        self.day.setDate(QDate.currentDate())
        self.refresh()

    @guarded
    def refresh(self) -> None:
        day, period = self.day.date().toPython(), self.period.currentData()
        routine = self.schedule.routine(day, period, area=self.area.currentText())
        completed = self.schedule.completed(day, period)
        products = {p.id: p for p in self.inventory.list()}
        self.steps.blockSignals(True)
        try:
            self.steps.clear()
            for i, step in enumerate(routine["steps"], 1):
                suffix = " • optional" if step["optional"] else ""
                suffix += " • REVIEW" if step["review"] else ""
                product = products.get(step["product_id"])
                if step["product_id"] is not None:
                    if product is None:
                        suffix += " • deleted product; edit your plan"
                    elif product.status != "Active":
                        suffix += f" • {product.status}"
                item = QListWidgetItem(f"{i:02}   {step['label']}{suffix}")
                instructions = step.get("instructions", "")
                skip = step.get("skip_conditions", "")
                item.setToolTip(f"{item.text()}\n{instructions}\n{skip}")
                item.setData(Qt.ItemDataRole.UserRole, step)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if step["product_id"] is not None and (
                    product is None or product.status in ("Paused", "Archived")
                ):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(
                    Qt.CheckState.Checked if step["id"] in completed else Qt.CheckState.Unchecked
                )
                item.setSizeHint(QSize(0, 58))
                self.steps.addItem(item)
        finally:
            self.steps.blockSignals(False)
        scope = "One-off override" if routine["overridden"] else "Weekly schedule"
        shower = " • Shower routine" if routine["shower"] else ""
        self.notice.setText(
            f"{routine.get('name', scope)} · {scope}{shower}. Hover a step for product directions."
        )
        if routine.get("session_merge_review"):
            self.notice.setText(
                self.notice.text() + " Converted sessions were combined; review their order."
            )
        self.warnings.update_findings(self.safety.review(day))
        upcoming = self.schedule.next_treatment(day, period)
        self.next_label.setText(
            f"Next treatment / review: {upcoming[0]:%a, %b %d} • {upcoming[1]}"
            if upcoming
            else "No treatment planned in the next 62 days."
        )
        self.refresh_history()

    def refresh_history(self) -> None:
        records = self.schedule.history()
        self.history.setRowCount(len(records))
        for row, record in enumerate(records):
            for column, value in enumerate((record.day.isoformat(), record.period, record.label)):
                self.history.setItem(row, column, QTableWidgetItem(value))

    @guarded
    def mark(self, item: QListWidgetItem) -> None:
        self.schedule.mark(
            self.day.date().toPython(),
            self.period.currentData(),
            item.data(Qt.ItemDataRole.UserRole),
            item.checkState() == Qt.CheckState.Checked,
        )
        self.refresh_history()


class InventoryPage(QWidget):
    def __init__(self, inventory: InventoryService):
        super().__init__()
        self.inventory = inventory
        layout = QVBoxLayout(self)
        title(
            layout, "Your product shelf", "Know what you own. Keep the details that matter to you."
        )
        from PySide6.QtWidgets import QLineEdit

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search products, brands, or active ingredients…")
        self.category, self.status = QComboBox(), QComboBox()
        self.category.addItems(("All", *CATEGORIES))
        self.status.addItems(("All", *STATUSES))
        row = QHBoxLayout()
        row.addWidget(self.search, 2)
        row.addWidget(self.category)
        row.addWidget(self.status)
        self.add_button = action("+ Add product", self.add, row)
        layout.addLayout(row)
        self.count = QLabel()
        layout.addWidget(self.count)
        self.products = QListWidget()
        self.products.setSpacing(8)
        self.products.itemDoubleClicked.connect(lambda _item: self.edit())
        layout.addWidget(self.products)
        row = QHBoxLayout()
        action("Edit selected", self.edit, row)
        action("Archive", self.archive, row)
        action("Delete", self.delete, row)
        row.addStretch()
        layout.addLayout(row)
        self.search.textChanged.connect(lambda _text: self.refresh())
        self.category.currentTextChanged.connect(lambda _text: self.refresh())
        self.status.currentTextChanged.connect(lambda _text: self.refresh())

    @guarded
    def refresh(self) -> None:
        selected = self.selected_id()
        self.products.clear()
        products = self.inventory.list(
            self.search.text(), self.category.currentText(), self.status.currentText()
        )
        self.count.setText(f"{len(products)} products • Double-click a card to edit")
        for product in products:
            verified = (
                "Ingredients verified" if product.ingredients_verified else "Ingredients unverified"
            )
            item = QListWidgetItem(
                f"{product.label}\n"
                f"{product.category}   ·   {product.status}   ·   {verified}\n"
                f"{product.actives or 'Active ingredients unknown / unverified'}"
            )
            item.setSizeHint(QSize(0, 94))
            item.setData(Qt.ItemDataRole.UserRole, product.id)
            self.products.addItem(item)
            if product.id == selected:
                self.products.setCurrentItem(item)

    def selected_id(self) -> int | None:
        item = self.products.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def add(self) -> None:
        if ProductDialog(self, self.inventory).exec():
            self.refresh()

    @guarded
    def edit(self) -> None:
        product_id = self.selected_id()
        if product_id is not None:
            if ProductDialog(self, self.inventory, self.inventory.get(product_id)).exec():
                self.refresh()

    @guarded
    def archive(self) -> None:
        product_id = self.selected_id()
        if product_id is not None:
            self.inventory.archive(product_id)
            self.refresh()

    @guarded
    def delete(self) -> None:
        product_id = self.selected_id()
        if product_id is not None and confirm(
            self,
            "Delete product?",
            "Remove this product from your shelf? Historical records will be retained. "
            "Existing routine steps will remain visible so you can edit them.",
        ):
            self.inventory.delete(product_id)
            self.refresh()


class CalendarPage(QWidget):
    def __init__(
        self, inventory: InventoryService, schedule: ScheduleService, safety: SafetyService
    ):
        super().__init__()
        self.inventory, self.schedule = inventory, schedule
        self.safety = safety
        layout = QVBoxLayout(self)
        title(layout, "A rhythm for your week", "Select a session to edit its ordered steps.")
        row = QHBoxLayout()
        action("‹ Previous", lambda: self.shift(-7), row)
        self.day = date_picker()
        row.addWidget(self.day)
        self.area = QComboBox()
        self.area.addItems(("Face", "Scalp"))
        row.addWidget(self.area)
        action("Next ›", lambda: self.shift(7), row)
        row.addStretch()
        action("Monthly treatments…", self.monthly, row)
        action("Version history…", self.history, row)
        layout.addLayout(row)
        notice = QLabel(
            "Date overrides replace one session. Monthly treatments marked for review wait for "
            "approval. Move a Scalp session to move shower/scalp care while keeping "
            "facial products in place."
        )
        notice.setObjectName("notice")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.warnings = SafetyPanel()
        layout.addWidget(self.warnings)
        extras = QHBoxLayout()
        action("Monthly occurrence…", self.review_monthly, extras)
        action("Recovery override…", self.recovery, extras)
        action("Saved routine templates…", self.templates, extras)
        extras.addStretch()
        layout.addLayout(extras)
        self.table = QTableWidget(7, len(PERIODS))
        self.table.setHorizontalHeaderLabels(PERIOD_LABELS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.edit())
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.scope = QComboBox()
        self.scope.addItems(("Only this date", "Every week (base schedule)"))
        row.addWidget(self.scope)
        self.edit_button = action("Edit selected routine…", self.edit, row)
        action("Clear date override", self.clear_override, row)
        action("Move to another date…", self.move, row)
        row.addStretch()
        layout.addLayout(row)
        self.day.dateChanged.connect(lambda _date: self.refresh())
        self.area.currentTextChanged.connect(lambda _text: self.refresh())
        self.table.setCurrentCell(date.today().weekday(), 0)

    def shift(self, offset: int) -> None:
        self.day.setDate(self.day.date().addDays(offset))

    @guarded
    def refresh(self) -> None:
        self.week_data = self.schedule.week(self.day.date().toPython(), self.area.currentText())
        self.table.setVerticalHeaderLabels(
            [entry[0].strftime("%a\n%b %d") for entry in self.week_data]
        )
        for row, (_day, *routines) in enumerate(self.week_data):
            for column, routine in enumerate(routines):
                heading = "SHOWER  " if routine["shower"] else ""
                heading += "ONE-OFF" if routine["overridden"] else "WEEKLY"
                if routine.get("session_merge_review"):
                    heading += " · REVIEW COMBINED ORDER"
                lines = [heading] + [
                    f"{i}. {step['label']}"
                    f"{' (optional)' if step['optional'] else ''}"
                    f"{' [REVIEW]' if step['review'] else ''}"
                    for i, step in enumerate(routine["steps"], 1)
                ]
                item = QTableWidgetItem("\n".join(lines))
                item.setToolTip("\n".join(lines))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()
        for row in range(7):
            self.table.setRowHeight(row, max(82, self.table.rowHeight(row)))
        self.warnings.update_findings(
            self.safety.review(self.week_data[0][0], self.week_data[-1][0])
        )

    def selection(self) -> tuple[date, str]:
        row, column = self.table.currentRow(), self.table.currentColumn()
        if row < 0 or column < 0:
            raise ValueError("Select a routine first.")
        return self.week_data[row][0], PERIODS[column]

    @guarded
    def edit(self) -> None:
        day, period = self.selection()
        weekly = self.scope.currentIndex() == 1
        payload, version = self.schedule.snapshot()
        area = self.area.currentText()
        routine = (
            payload["scalp" if area == "Scalp" else "weekly"][f"{day.weekday()}:{period}"]
            if weekly
            else self.schedule.routine(day, period, payload, area)
        )
        dialog = RoutineDialog(
            self,
            self.inventory,
            routine,
            f"{day:%A, %b %d} {period} • {'weekly base' if weekly else 'one-off'}",
        )
        if dialog.exec():
            self.schedule.set_routine(
                day,
                period,
                dialog.result_routine,
                weekly=weekly,
                expected_version=version,
                area=area,
            )
            self.refresh()

    @guarded
    def clear_override(self) -> None:
        day, period = self.selection()
        self.schedule.clear_override(day, period, self.area.currentText())
        self.refresh()

    @guarded
    def move(self) -> None:
        day, period = self.selection()
        dialog = QDialog(self)
        dialog.setWindowTitle("Move one routine")
        layout = QVBoxLayout(dialog)
        text = QLabel(
            f"Move {day:%a, %b %d} {period} to another date.\n"
            "This replaces the target routine and leaves the source empty.\n"
            "Completions stay on their dates. Review the changes and warnings next."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        target = date_picker(day + timedelta(days=1))
        layout.addWidget(target)
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(dialog.accept)
        box.rejected.connect(dialog.reject)
        layout.addWidget(box)
        if dialog.exec():
            target_day = target.date().toPython()
            payload, version = self.schedule.preview_move(
                day, target_day, period, self.area.currentText()
            )
            self.review(
                payload,
                version,
                "Review moved routine",
                f"Moved {self.area.currentText()} {day} to {target_day}",
                min(day, target_day),
                max(day, target_day),
            )

    def review(
        self,
        payload: dict,
        version: int,
        heading: str,
        description: str,
        start: date,
        end: date | None = None,
    ) -> None:
        dialog = ScheduleReviewDialog(
            self, self.schedule, self.safety, payload, version, heading, description, start, end
        )
        if dialog.exec():
            self.refresh()

    @guarded
    def review_monthly(self) -> None:
        day, _period = self.selection()
        rules = self.schedule.monthly_occurrences(day)
        if not rules:
            raise ValueError(
                "Select a date with a monthly treatment (for example, the first Saturday)."
            )
        name, selected = QInputDialog.getItem(
            self, "Monthly treatment", "Treatment", [r["name"] for r in rules], 0, False
        )
        if not selected:
            return
        rule = next(r for r in rules if r["name"] == name)
        choice, selected = QInputDialog.getItem(
            self,
            "Review or skip",
            "This occurrence",
            ("Review treatment and recovery changes", "Skip this occurrence (keep normal routine)"),
            0,
            False,
        )
        if selected:
            payload, version = self.schedule.monthly_preview(
                rule["id"], day, choice.startswith("Review")
            )
            self.review(
                payload,
                version,
                "Monthly treatment and skin-condition review",
                f"{'Approved' if choice.startswith('Review') else 'Skipped'} {rule['name']} {day}",
                day - timedelta(days=rule.get("recovery_before", 0)),
                day + timedelta(days=rule.get("recovery_after", 0)),
            )

    @guarded
    def recovery(self) -> None:
        day, _period = self.selection()
        before, selected = QInputDialog.getInt(
            self, "Recovery days", "Days before selected date", 0, 0, 7
        )
        if not selected:
            return
        after, selected = QInputDialog.getInt(
            self, "Recovery days", "Days after selected date", 0, 0, 7
        )
        if selected:
            payload, version = self.schedule.recovery_preview(day, before, after)
            self.review(
                payload,
                version,
                "Review recovery overrides",
                f"Recovery overrides around {day}",
                day - timedelta(days=before),
                day + timedelta(days=after),
            )

    @guarded
    def templates(self) -> None:
        templates = self.schedule.templates()
        name, selected = QInputDialog.getItem(
            self,
            "Saved routine templates",
            "Replace the plan with",
            [t.name for t in templates],
            0,
            False,
        )
        if selected:
            template = next(t for t in templates if t.name == name)
            payload, version = self.schedule.template_preview(template.id)
            start = self.day.date().toPython()
            self.review(
                payload,
                version,
                "Review routine template",
                f"Loaded template: {name}",
                start,
                start + timedelta(days=6),
            )

    def monthly(self) -> None:
        if MonthlyDialog(self, self.inventory, self.schedule).exec():
            self.refresh()

    @guarded
    def history(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Schedule version history")
        dialog.resize(740, 450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel("Restore weekly, monthly, and one-off plans. Completion records stay intact.")
        )
        table = readonly_table(["Version", "Saved (local time)", "Change"])
        revisions = self.schedule.revisions()
        table.setRowCount(len(revisions))
        for row, revision in enumerate(revisions):
            # Timestamps are stored in UTC; SQLite returns naive values.
            from datetime import timezone

            stamp = revision.created_at.replace(tzinfo=timezone.utc).astimezone()
            for column, value in enumerate(
                (str(revision.id), stamp.strftime("%Y-%m-%d %H:%M"), revision.description)
            ):
                table.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(table)

        @guarded
        def restore(_page):
            row = table.currentRow()
            if row >= 0 and confirm(
                dialog, "Restore schedule?", "Restore this saved schedule as a new version?"
            ):
                self.schedule.rollback(revisions[row].id)
                dialog.accept()
                self.refresh()

        action("Restore selected version", lambda: restore(self), layout)
        action("Close", dialog.reject, layout)
        dialog.exec()


class SettingsPage(QWidget):
    def __init__(self, database, settings: SettingsService, theme_callback):
        super().__init__()
        self.db, self.settings = database, settings
        layout = QVBoxLayout(self)
        title(layout, "Make it yours", "Your inventory and routines live on this computer.")
        self.dark = QCheckBox("Dark theme")
        self.dark.setChecked(settings.get("theme", "light") == "dark")
        self.dark.toggled.connect(theme_callback)
        layout.addWidget(self.dark)
        location = QLabel(f"Database: {database.path}")
        location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        location.setWordWrap(True)
        layout.addWidget(location)
        action("Save database backup…", self.backup, layout)
        self.result = QLabel()
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        roadmap = QLabel(
            "Phase 2 • Morning and Night routines, separate scalp care, safety warnings, "
            "skin observations, and approved recovery changes.\n\n"
            "Coming in Phase 3: optional AI chat with data-sharing controls and "
            "explicit approval of every proposed routine change.\n\n"
            "Phase 4: import/export, guided restore, and distribution polish.\n\n"
            "No API key is needed. The application makes no network requests."
        )
        roadmap.setWordWrap(True)
        layout.addWidget(roadmap)
        layout.addWidget(QLabel("Personal caution preferences (not universal medical limits)"))
        self.gap = QSpinBox()
        self.gap.setRange(0, 168)
        self.gap.setSuffix(" hours between active sessions")
        self.gap.setValue(int(settings.get("active_gap_hours", "48")))
        self.exfoliation = QSpinBox()
        self.exfoliation.setRange(1, 14)
        self.exfoliation.setSuffix(" exfoliation sessions per 7 days")
        self.exfoliation.setValue(int(settings.get("max_exfoliation_sessions", "1")))
        layout.addWidget(self.gap)
        layout.addWidget(self.exfoliation)
        action("Save caution preferences", self.save_policy, layout)
        layout.addStretch()

    @guarded
    def save_policy(self) -> None:
        self.settings.set("active_gap_hours", str(self.gap.value()))
        self.settings.set("max_exfoliation_sessions", str(self.exfoliation.value()))
        self.result.setText("Caution preferences saved. Reviews use them when refreshed.")

    @guarded
    def backup(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(
            self, "Save database backup", f"skinflow-backup-{date.today()}.db", "SQLite (*.db)"
        )
        if path:
            self.db.backup(Path(path))
            self.result.setText(f"Backup saved to {path}")

    def refresh(self) -> None:
        pass
