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
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skinflow.services import (
    CATEGORIES,
    STATUSES,
    InventoryService,
    ScheduleService,
    SettingsService,
)
from skinflow.ui.common import confirm, guarded
from skinflow.ui.dialogs import MonthlyDialog, ProductDialog, RoutineDialog


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
    def __init__(self, inventory: InventoryService, schedule: ScheduleService):
        super().__init__()
        self.inventory, self.schedule = inventory, schedule
        layout = QVBoxLayout(self)
        title(layout, "Your daily ritual", "An editable plan, one step at a time.")
        row = QHBoxLayout()
        self.day = date_picker()
        self.period = QComboBox()
        self.period.addItems(("AM", "PM"))
        self.period.setCurrentText("AM" if datetime.now().hour < 12 else "PM")
        row.addWidget(self.day)
        row.addWidget(self.period)
        row.addStretch()
        action("Today", self.today, row)
        layout.addLayout(row)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.steps = QListWidget()
        self.steps.setSpacing(6)
        self.steps.itemChanged.connect(self.mark)
        layout.addWidget(self.steps, 2)
        self.next_label = QLabel()
        self.next_label.setWordWrap(True)
        layout.addWidget(self.next_label)
        layout.addWidget(QLabel("Recent completions • recorded separately from your plan"))
        self.history = readonly_table(["Date", "AM / PM", "Completed step"])
        layout.addWidget(self.history, 1)
        self.day.dateChanged.connect(lambda _date: self.refresh())
        self.period.currentTextChanged.connect(lambda _text: self.refresh())

    def today(self) -> None:
        self.day.setDate(QDate.currentDate())
        self.refresh()

    @guarded
    def refresh(self) -> None:
        day, period = self.day.date().toPython(), self.period.currentText()
        routine = self.schedule.routine(day, period)
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
                item.setToolTip(item.text())
                item.setData(Qt.ItemDataRole.UserRole, step)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if step["id"] in completed else Qt.CheckState.Unchecked
                )
                item.setSizeHint(QSize(0, 58))
                self.steps.addItem(item)
        finally:
            self.steps.blockSignals(False)
        scope = "One-off override" if routine["overridden"] else "Baseline schedule"
        shower = " • Shower routine" if routine["shower"] else ""
        self.notice.setText(f"{scope}{shower}. Ingredient conflict warnings arrive in Phase 2.")
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
            self.period.currentText(),
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
    def __init__(self, inventory: InventoryService, schedule: ScheduleService):
        super().__init__()
        self.inventory, self.schedule = inventory, schedule
        layout = QVBoxLayout(self)
        title(
            layout, "A rhythm for your week", "Select an AM or PM cell to edit its ordered steps."
        )
        row = QHBoxLayout()
        action("‹ Previous", lambda: self.shift(-7), row)
        self.day = date_picker()
        row.addWidget(self.day)
        action("Next ›", lambda: self.shift(7), row)
        row.addStretch()
        action("Monthly treatments…", self.monthly, row)
        action("Version history…", self.history, row)
        layout.addLayout(row)
        notice = QLabel(
            "One-off edits replace that date's routine. Monthly treatments append to the "
            "baseline. Review treatment spacing when moving routines; automatic conflict "
            "checking arrives in Phase 2."
        )
        notice.setObjectName("notice")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.table = QTableWidget(7, 2)
        self.table.setHorizontalHeaderLabels(("AM", "PM"))
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
        self.table.setCurrentCell(date.today().weekday(), 0)

    def shift(self, offset: int) -> None:
        self.day.setDate(self.day.date().addDays(offset))

    @guarded
    def refresh(self) -> None:
        self.week_data = self.schedule.week(self.day.date().toPython())
        self.table.setVerticalHeaderLabels(
            [day.strftime("%a\n%b %d") for day, _am, _pm in self.week_data]
        )
        for row, (_day, am, pm) in enumerate(self.week_data):
            max_steps = max(len(am["steps"]), len(pm["steps"]))
            self.table.setRowHeight(row, max(115, 34 + max_steps * 26))
            for column, routine in enumerate((am, pm)):
                heading = "SHOWER  " if routine["shower"] else ""
                heading += "ONE-OFF" if routine["overridden"] else "BASELINE"
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

    def selection(self) -> tuple[date, str]:
        row, column = self.table.currentRow(), self.table.currentColumn()
        if row < 0 or column < 0:
            raise ValueError("Select an AM or PM routine first.")
        return self.week_data[row][0], ("AM", "PM")[column]

    @guarded
    def edit(self) -> None:
        day, period = self.selection()
        weekly = self.scope.currentIndex() == 1
        payload, version = self.schedule.snapshot()
        routine = (
            payload["weekly"][f"{day.weekday()}:{period}"]
            if weekly
            else self.schedule.routine(day, period, payload)
        )
        dialog = RoutineDialog(
            self,
            self.inventory,
            routine,
            f"{day:%A, %b %d} {period} • {'weekly base' if weekly else 'one-off'}",
        )
        if dialog.exec():
            self.schedule.set_routine(
                day, period, dialog.result_routine, weekly=weekly, expected_version=version
            )
            self.refresh()

    @guarded
    def clear_override(self) -> None:
        day, period = self.selection()
        self.schedule.clear_override(day, period)
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
            "Completions stay on their original dates. Review treatment spacing yourself."
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
            self.schedule.move(day, target.date().toPython(), period)
            self.refresh()

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
            "Phase 1 • Inventory and editable calendar\n\n"
            "Coming in Phase 2: ingredient warnings, treatment spacing checks, "
            "skin observations, and recovery-day assistance.\n\n"
            "Coming in Phase 3: optional AI chat with data-sharing controls and "
            "explicit approval of every proposed routine change.\n\n"
            "Phase 4: import/export, guided restore, and distribution polish.\n\n"
            "No API key is needed. Phase 1 makes no network requests."
        )
        roadmap.setWordWrap(True)
        layout.addWidget(roadmap)
        layout.addStretch()

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
