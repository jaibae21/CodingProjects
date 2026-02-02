from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import cv2
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QComboBox, QMessageBox
)

@dataclass
class CameraConfig:
    device_index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30

class CameraWidget(QWidget):
    """
    Docstring for CameraWidget
    Simple camera preview widget using OpenCV and QTimer

    - Start/Stop controls
    - Device selection
    - Emits latest_frame_bgr when a new frame arrives (optional use later for OCR)
    """

    latest_frame_bgr = Signal(object)  # Emits the latest frame in BGR format

    def __init__(self, *, max_devices: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config = CameraConfig()
        self._cap: Optional[cv2.VideoCapture] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # UI
        self.preview = QLabel("Camera Preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(240)
        self.preview.setStyleSheet(
            "QLabel {background: #111; color: #bbb; border: 1px solid #333;}"
        )

        self.device_combo = QComboBox()
        for i in range(max_devices):
            self.device_combo.addItem(f"Camera {i}", i)
        self.device_combo.setCurrentIndex(self.config.device_index)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        self.btn_start = QPushButton("Start Camera")
        self.btn_stop = QPushButton("Stop Camera")
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Device:"))
        top_row.addWidget(self.device_combo)
        top_row.addStretch(1)
        top_row.addWidget(self.btn_start)
        top_row.addWidget(self.btn_stop)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.preview)
    
    def is_running(self) -> bool:
        return self._cap is not None and self._cap.isOpened() and self.timer.isActive()
    
    def start(self) -> None:
        if self.is_running():
            return
        
        device_index = int(self.device_combo.currentData())
        cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW) # Cap DSHOW helps for windows
        if not cap.isOpened():
            # Try without backend hint (helps on mac/linux)
            cap.release()
            cap  = cv2.VideoCapture(device_index)
        if not cap.isOpened():
            QMessageBox.critical(self, "Camera Error", f"Failed to open camera device {device_index}.")
            return
        
        # Configure (best-effot; not all cameras obey)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        cap.set(cv2.CAP_PROP_FPS, self.config.fps)

        self._cap = cap

        interval_ms = max(1, int(1000 / max(1, self.config.fps)))
        self._timer.start(interval_ms)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
    
    def stop(self) -> None:
        self._timer.stop()

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        self.preview.setText("Camera Preview")
        self.preview.setPixmap(QPixmap())
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def grab_current_frame(self):
        """
        Optional helper: returns last read frame by doing single capture read now
        """
        if self._cap is None or not self._cap.isOpened():
            return None
        ok, frame = self._cap.read()
        return frame if ok else None
    
    def closeEvent(self, event) -> None:
        # Ensure camera is relased when widget closes
        self.stop()
        super().closeEvent(event)

    # ----------------------------
    # Internal
    # ---------------------------

    def _on_device_changed(self, _idx: int) -> None:
        self.config.device_index = int(self.device_combo.currentData())
        if self.is_running():
            # Restart on device switch
            self.stop()
            self.start()
        
    def _on_tick(self) -> None:
        if self._cap is None or not self._cap.isOpened():
            self.stop()
            return
        
        ok, frame_bgr = self._cap.read()
        if not ok or frame_bgr is None:
            return
        
        self.latest_frame_bgr.emit(frame_bgr)

        # Convert BGR to RGB for Qt
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to fit label while preserving aspect ratio
        pix = QPixmap.fromImage(qimg)
        pix = pix.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pix)

    def resizeEvent(self, event) -> None:
        # When the widget resizes, next tick will rescale
        return super().resizeEvent(event)
