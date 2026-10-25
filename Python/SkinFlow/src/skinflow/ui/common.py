import logging
from functools import wraps

from PySide6.QtWidgets import QMessageBox


def guarded(action):
    """Keep service errors out of Qt's event loop and preserve transactional failures."""

    @wraps(action)
    def wrapped(self, *args, **kwargs):
        try:
            return action(self, *args, **kwargs)
        except ValueError as error:
            QMessageBox.warning(self, "Please check", str(error))
        except Exception:
            logging.getLogger(__name__).exception("UI action failed: %s", action.__name__)
            QMessageBox.critical(
                self,
                "Unable to complete action",
                "The action failed. Check skinflow.log in the data folder.",
            )
        return None

    return wrapped


def confirm(parent, title: str, message: str) -> bool:
    return QMessageBox.question(parent, title, message) == QMessageBox.StandardButton.Yes
