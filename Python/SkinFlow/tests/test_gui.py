from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from skinflow.services import SettingsService, empty_routine, new_step
from skinflow.ui.dialogs import ProductDialog, RoutineDialog, StepDialog
from skinflow.ui.window import MainWindow


def test_sidebar_search_and_theme(qtbot, db):
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.show()
    window.navigation.setCurrentRow(1)
    assert window.inventory.products.count() == 24
    window.inventory.search.setText("Resurfacing Retinol")
    assert window.inventory.products.count() == 1
    window.navigation.setCurrentRow(2)
    assert window.calendar.table.rowCount() == 7
    window.navigation.setCurrentRow(4)
    settings = window.stack.widget(4)
    settings.dark.setChecked(True)
    assert SettingsService(db).get("theme") == "dark"
    window.navigation.setCurrentRow(0)
    assert window.dashboard.steps.count() >= 3


def test_product_form_creates_and_edits_persisted_product(qtbot, inventory):
    dialog = ProductDialog(None, inventory)
    qtbot.addWidget(dialog)
    dialog.fields["brand"].setText("Test Brand")
    dialog.fields["name"].setText("Test Moisturizer")
    dialog.fields["category"].setCurrentText("Moisturizer")
    dialog.fields["ingredients"].setPlainText("Water")
    dialog.verified.setChecked(True)
    dialog.fields["opened_on"].setText("2026-10-25")
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    product = inventory.list(search="Test Moisturizer")[0]
    assert product.ingredients_verified and product.opened_on == date(2026, 10, 25)
    edit = ProductDialog(None, inventory, product)
    qtbot.addWidget(edit)
    edit.fields["status"].setCurrentText("Paused")
    edit.accept()
    assert inventory.get(product.id).status == "Paused"


def test_dashboard_checkbox_persists_completion(qtbot, db, schedule):
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.dashboard.period.setCurrentIndex(0)
    item = window.dashboard.steps.item(0)
    item.setCheckState(Qt.CheckState.Checked)
    assert len(schedule.completed(date.today(), "AM")) == 1
    window.dashboard.refresh()
    assert window.dashboard.steps.item(0).checkState() == Qt.CheckState.Checked
    window.dashboard.steps.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert not schedule.completed(date.today(), "AM")


def test_routine_editor_reorders_without_mutating_original(qtbot, inventory):
    original = {"shower": False, "steps": [new_step("First"), new_step("Second")]}
    editor = RoutineDialog(None, inventory, original, "Test routine")
    qtbot.addWidget(editor)
    editor.steps.setCurrentRow(1)
    editor.reorder(-1)
    editor.shower.setChecked(True)
    editor.accept()
    assert editor.result_routine["steps"][0]["label"] == "Second"
    assert editor.result_routine["shower"]
    assert original["steps"][0]["label"] == "First"


def test_calendar_edit_action_saves_only_selected_date(qtbot, monkeypatch, db, schedule):
    window = MainWindow(db)
    qtbot.addWidget(window)
    window.navigation.setCurrentRow(2)
    calendar = window.calendar
    calendar.table.setCurrentCell(1, 1)
    day, period = calendar.selection()
    baseline = schedule.snapshot()[0]["weekly"]

    def accept_edit(dialog):
        dialog.result_routine = empty_routine()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(RoutineDialog, "exec", accept_edit)
    calendar.edit_button.click()
    assert schedule.routine(day, period)["steps"] == []
    assert schedule.snapshot()[0]["weekly"] == baseline


def test_step_editor_can_keep_deleted_product_reference(qtbot, inventory):
    product = inventory.list()[0]
    step = new_step(product.label, product.id)
    inventory.delete(product.id)
    editor = StepDialog(None, inventory, step)
    qtbot.addWidget(editor)
    editor.accept()
    assert editor.result_step["product_id"] == product.id
    assert editor.result_step["id"] == step["id"]
