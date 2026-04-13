from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import cv2
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QComboBox, QMessageBox
)

# MTG cards are roughly 63x88mm so aspect ratio is 0.716
CARD_ASPECT_RATIO = 63.0 / 88.0 # width / height
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
        return self._cap is not None and self._cap.isOpened() and self._timer.isActive()
    
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
    
    def save_current_frame(self, output_dir: str | Path) -> Path | None:
        """
        Capture the current frame from the camera and save it to disk with a timestamped filename.
        
        Returns: Path to the saved file, or None if captured
        """
        frame = self.grab_current_frame()
        if frame is None:
            return None
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"capture_{timestamp}.jpg"

        ok = cv2.imwrite(str(out_path), frame)
        if not ok:
            return None
        
        return out_path

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

        # Live Guide box
        display_frame = frame_bgr.copy()
        h,w = display_frame.shape[:2]
        guide_w = int(w * 0.42)
        guide_h = int(guide_w / CARD_ASPECT_RATIO)
        
        if guide_h > h * 0.80:
            guide_h = int(h * 0.80)
            guide_w = int(guide_h * CARD_ASPECT_RATIO)

        x1 = (w - guide_w) // 2
        y1 = (h - guide_h) // 2
        x2 = x1 + guide_w
        y2 = y1 + guide_h

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Convert BGR to RGB for Qt
        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
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
