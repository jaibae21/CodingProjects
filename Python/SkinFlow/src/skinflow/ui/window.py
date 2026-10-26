from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from skinflow.database import Database
from skinflow.safety.service import SafetyService
from skinflow.services import InventoryService, ScheduleService, SettingsService
from skinflow.tracking import ObservationService
from skinflow.ui.common import guarded
from skinflow.ui.pages import CalendarPage, DashboardPage, InventoryPage, SettingsPage
from skinflow.ui.tracking_views import TrackingPage


class MainWindow(QMainWindow):
    def __init__(self, database: Database):
        super().__init__()
        self.setWindowTitle("SkinFlow • Your personal routine")
        self.resize(1280, 880)
        self.setMinimumSize(960, 660)
        self.settings = SettingsService(database)
        inventory, schedule = InventoryService(database), ScheduleService(database)
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(205)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 26, 18, 22)
        brand = QLabel("SkinFlow")
        brand.setObjectName("brand")
        side.addWidget(brand)
        side.addWidget(QLabel("Care, at your own pace."))
        side.addSpacing(32)
        self.navigation = QListWidget()
        self.navigation.addItems(
            ("Today", "Product shelf", "Routine calendar", "Skin tracker", "Settings")
        )
        self.navigation.setSpacing(6)
        for index in range(self.navigation.count()):
            self.navigation.item(index).setSizeHint(QSize(0, 46))
        side.addWidget(self.navigation)
        side.addWidget(QLabel("LOCAL & OFFLINE\nPhase 2 · v0.2.1"))
        layout.addWidget(sidebar)
        self.stack = QStackedWidget()
        safety = SafetyService(database)
        self.dashboard = DashboardPage(inventory, schedule, safety)
        self.inventory = InventoryPage(inventory)
        self.calendar = CalendarPage(inventory, schedule, safety)
        self.tracking = TrackingPage(ObservationService(database))
        for page in (
            self.dashboard,
            self.inventory,
            self.calendar,
            self.tracking,
            SettingsPage(database, self.settings, self.apply_theme),
        ):
            page.layout().setContentsMargins(28, 24, 28, 24)
            page.layout().setSpacing(14)
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(body)
        self.statusBar().showMessage("Saved locally • No account or internet connection required")
        self.navigation.currentRowChanged.connect(self.navigate)
        self.apply_theme(self.settings.get("theme", "light") == "dark")
        self.navigation.setCurrentRow(0)

    @guarded
    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.stack.widget(index).refresh()

    @guarded
    def apply_theme(self, dark: bool) -> None:
        self.settings.set("theme", "dark" if dark else "light")
        bg, card, fg, muted, edge, accent, tint = (
            ("#17211f", "#222f2b", "#edf4ef", "#aebfb6", "#3b4e45", "#9cd8ba", "#344a3e")
            if dark
            else ("#f6f7f2", "#ffffff", "#263e34", "#61756a", "#dce5dc", "#2b7254", "#e5f0e5")
        )
        palette = QPalette()
        roles = {
            QPalette.ColorRole.Window: bg,
            QPalette.ColorRole.WindowText: fg,
            QPalette.ColorRole.Base: card,
            QPalette.ColorRole.AlternateBase: tint,
            QPalette.ColorRole.Text: fg,
            QPalette.ColorRole.Button: card,
            QPalette.ColorRole.ButtonText: fg,
            QPalette.ColorRole.Highlight: tint,
            QPalette.ColorRole.HighlightedText: fg,
            QPalette.ColorRole.ToolTipBase: card,
            QPalette.ColorRole.ToolTipText: fg,
            QPalette.ColorRole.PlaceholderText: muted,
            QPalette.ColorRole.Link: accent,
        }
        for role, color in roles.items():
            palette.setColor(role, QColor(color))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(muted))
        application = QApplication.instance()
        application.setPalette(palette)
        application.styleHints().setColorScheme(
            Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light
        )
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI'; font-size: 13px; color: {fg}; }}
            QMainWindow, QStackedWidget, QDialog {{ background: {bg}; }}
            QComboBox QAbstractItemView, QCalendarWidget QAbstractItemView {{
                background-color: {card}; color: {fg};
                selection-background-color: {tint}; selection-color: {fg};
            }}
            QMenu {{ background: {card}; color: {fg}; }}
            QMenu::item:selected {{ background: {tint}; }}
            QTabWidget::pane {{ background: {card}; border: 1px solid {edge}; }}
            QTabBar::tab {{ background: {tint}; color: {fg}; padding: 10px; }}
            QSpinBox {{ background: {card}; color: {fg}; border: 1px solid {edge}; padding: 6px; }}
            QWidget#sidebar {{ background: {tint}; }}
            QLabel#brand {{ font-size: 30px; font-weight: 700; color: {accent}; }}
            QLabel#pageTitle {{ font-size: 28px; font-weight: 600; }}
            QLabel#subtitle {{ color: {muted}; font-size: 14px; }}
            QLabel#notice {{ background: {tint}; padding: 12px; border-radius: 8px; }}
            QListWidget, QTableWidget, QLineEdit, QPlainTextEdit, QComboBox, QDateEdit {{
                background: {card}; border: 1px solid {edge}; border-radius: 6px; padding: 6px;
                selection-background-color: {tint}; selection-color: {fg};
            }}
            QListWidget::item {{ padding: 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {tint}; color: {fg}; }}
            QPushButton {{ background: {card}; border: 1px solid {edge}; padding: 9px 14px;
                           border-radius: 6px; font-weight: 600; }}
            QPushButton:hover {{ background: {tint}; border-color: {accent}; }}
            QPushButton:pressed {{ background: {edge}; }}
            QHeaderView::section {{ background: {tint}; color: {fg}; padding: 8px; border: 0; }}
            QTableWidget {{ gridline-color: {edge}; }}
            QScrollArea {{ border: 0; background: {bg}; }}
            QCheckBox {{ spacing: 8px; padding: 5px; }}
            QStatusBar {{ background: {tint}; color: {muted}; }}
            QToolTip {{ background: {card}; color: {fg}; border: 1px solid {edge}; }}
        """)
