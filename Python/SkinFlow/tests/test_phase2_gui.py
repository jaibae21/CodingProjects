from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QTabWidget

from skinflow.safety.service import SafetyService
from skinflow.tracking import ObservationService
from skinflow.ui.dialogs import MonthlyRuleDialog, ProductDialog, StepDialog
from skinflow.ui.safety_views import ScheduleReviewDialog
from skinflow.ui.tracking_views import ObservationDialog
from skinflow.ui.window import MainWindow


def test_two_periods_scalp_and_skin_tracker_navigation(qtbot, db):
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.show()
    assert window.dashboard.period.count() == 2
    window.dashboard.day.setDate(QDate(2026, 10, 27))
    window.dashboard.period.setCurrentIndex(1)
    assert window.dashboard.steps.count() == 4
    window.dashboard.area.setCurrentText("Scalp")
    assert window.dashboard.steps.count() == 3
    window.navigation.setCurrentRow(2)
    assert window.calendar.table.columnCount() == 2
    window.calendar.area.setCurrentText("Scalp")
    window.navigation.setCurrentRow(3)
    assert window.stack.currentWidget() is window.tracking


def test_new_monthly_rule_uses_night_and_only_two_choices(qtbot, inventory):
    dialog = MonthlyRuleDialog(None, inventory)
    qtbot.addWidget(dialog)
    assert dialog.period.count() == 2
    assert dialog.period.currentData() == "Night"
    dialog.accept()
    assert dialog.rule["period"] == "Night"


def test_light_theme_controls_override_a_dark_system_palette(qtbot, db):
    application = QApplication.instance()
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Base, QColor("#111111"))
    dark.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
    application.setPalette(dark)
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.apply_theme(False)
    dialog = ProductDialog(window, window.inventory.inventory)
    qtbot.addWidget(dialog)
    dialog.show()
    combo = dialog.fields["category"]
    combo.ensurePolished()
    popup = combo.view()
    popup.ensurePolished()
    assert application.palette().color(QPalette.ColorRole.Window).name() == "#f6f7f2"
    assert popup.palette().color(QPalette.ColorRole.Base).name() == "#ffffff"
    assert popup.palette().color(QPalette.ColorRole.Text).name() == "#263e34"


def test_review_cancel_and_explicit_approval(qtbot, db, schedule):
    day = date(2026, 11, 7)
    before = schedule.snapshot()
    payload, version = schedule.monthly_preview("monthly-aha-review", day, True)
    dialog = ScheduleReviewDialog(
        None,
        schedule,
        SafetyService(db),
        payload,
        version,
        "Review treatment",
        "Approved monthly treatment",
        day,
    )
    qtbot.addWidget(dialog)
    tabs = dialog.findChild(QTabWidget)
    assert tabs.widget(0).count() > 0 and tabs.widget(1).count() > 0
    dialog.reject()
    assert schedule.snapshot() == before
    approved = ScheduleReviewDialog(
        None,
        schedule,
        SafetyService(db),
        payload,
        version,
        "Review treatment",
        "Approved monthly treatment",
        day,
    )
    qtbot.addWidget(approved)
    approved.accept()
    assert approved.result() == QDialog.DialogCode.Accepted
    assert schedule.snapshot()[1] == version + 1


def test_observation_form_and_timeline_show_actual_product_use(qtbot, db, schedule):
    service = ObservationService(db)
    day = date(2026, 10, 27)
    step = schedule.routine(day, "Night")["steps"][1]
    schedule.mark(day, "Night", step, True)
    form = ObservationDialog(None, service)
    qtbot.addWidget(form)
    form.day.setDate(QDate(day))
    form.region.setCurrentText("Eyebrows")
    form.condition.setCurrentText("Stinging/Burning")
    form.notes.setPlainText("Stinging after a product; cause not established")
    form.painful.setChecked(True)
    form.accept()
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.navigation.setCurrentRow(3)
    assert window.tracking.table.rowCount() == 1
    assert "Nourishing Pads" in window.tracking.table.item(0, 2).text()
    window.tracking.table.selectRow(0)
    assert "professional evaluation" in window.tracking.details.text()
    window.dashboard.day.setDate(QDate(day))
    assert any(f.rule_id == "irritated_area" for f in window.dashboard.warnings.findings)


def test_product_safety_tags_and_step_substitution_can_be_edited(qtbot, inventory):
    product = inventory.list(search="Resurfacing Retinol")[0]
    form = ProductDialog(None, inventory, product)
    qtbot.addWidget(form)
    checked, source, note = form.tags["retinoid"]
    assert checked.isChecked()
    source.setCurrentIndex(1)
    note.setText("Verified against my label")
    form.accept()
    assert inventory.get(product.id).safety_tags["retinoid"]["source"] == "label_verified"
    editor = StepDialog(None, inventory)
    qtbot.addWidget(editor)
    editor.product.setCurrentIndex(editor.product.findData(product.id))
    editor.instructions.setPlainText("Use on dry skin")
    editor.skip_conditions.setText("Skip on irritated regions")
    editor.region.setCurrentText("Face")
    editor.substitutions.item(0).setSelected(True)
    editor.accept()
    assert editor.result_step["instructions"] == "Use on dry skin"
    assert editor.result_step["substitutions"]
    assert editor.result_step["product_id"] == product.id


def test_paused_products_are_visible_but_cannot_be_marked_as_used(qtbot, db, inventory):
    product = inventory.list(search="Daily Nourishing Pads")[0]
    inventory.save({"status": "Paused"}, product.id)
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.dashboard.day.setDate(QDate(2026, 10, 27))
    window.dashboard.period.setCurrentIndex(1)
    item = window.dashboard.steps.item(1)
    assert "Paused" in item.text()
    assert not item.flags() & Qt.ItemFlag.ItemIsEnabled
