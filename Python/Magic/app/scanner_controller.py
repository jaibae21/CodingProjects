from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

@dataclass
class ScannerConfig:
    roi_size: int = 220
    signature_size: int = 64

    # Difference threshold for "something changed" (card dectection)
    change_threshold: float = 8.0

    # Difference threshold for "stable enough"
    stable_threshold: float = 1.5

    # How long frame must stay stable
    stable_duration_sec: float = 0.35

    # Cooldown after successful trigger
    cooldown_sec: float = 1.0

class ScannerController(QObject):
    """
    Watches live frames and emits a trigger when
    1. Scene changes enough to count as a new card
    2. Scene becomes stable for short duration
    3. Cooldown is clear

    This is dectection/trigger only. No OCR or contour extraction yet.
    """
    status_changed = Signal(str)
    card_stable = Signal(object)  # Emits frame_bgr
    debug_changed = Signal(float, float) # change_score, stables_score

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self.config = ScannerConfig()
        self.enabled: bool = True
        self._processing_enabled: bool = True

        self._last_signatrue: Optional[np.ndarray] = None
        self._candidate_signature: Optional[np.ndarray] = None
        self._last_trigger_signature: Optional[np.ndarray] = None

        self._candidate_frame: Optional[np.ndarray] = None

        self._change_armed: bool = False
        self._stable_since: Optional[float] = None
        self._last_trigger_time: float = 0.0

        self._last_status: str = ""

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self._reset_state()
            self._set_status("Auto scan paused")
        else:
            self._set_status("Auto scan enabled")
        
    def reset(self) -> None:
        self._last_signatrue = None
        self._candidate_signature = None
        self._candidate_frame = None
        self._change_armed = False
        self._stable_since = None
    
    def force_rescan(self) -> None:
        self._last_trigger_signature = None
        self._last_trigger_time = 0.0
        self._change_armed = True
        self._stable_since = None
        self._set_status("Rescan armed")
    
    def process_frame(self, frame_bgr: np.ndarray) -> None:
        if not self.enabled or not self._processing_enabled:
            return
        
        now = time.monotonic()

        signature = self._compute_signature(frame_bgr)
        if signature is None:
            self._set_status("No usable frame")
            return
        
        if self._last_signatrue is None:
            self._last_signatrue = signature
            self._set_status("Watching for Card")
            return

        # Frame to frame difference score
        change_score = self._mean_abs_diff(signature, self._last_signatrue)
        self.debug_changed.emit(change_score, change_score)

        # Step 1: Arm, Has visible scene changed enought to start looking for stability
        if not self._change_armed:
            if change_score >= self.config.change_threshold:
                self._change_armed = True
                self._candidate_signature = signature
                self._candidate_frame = frame_bgr.copy()
                self._stable_since = None
                self._set_status("Change detected...")
        else:
            # Step 2: Once armed, watch whether candidate stays stable
            if change_score <= self.config.stable_threshold:
                if self._stable_since is None:
                    self._stable_since = now
                    self._candidate_frame = frame_bgr.copy()
                    self._set_status("Stabilizing...")
                else:
                    self._candidate_frame = frame_bgr.copy()
                    if (now - self._stable_since) >= self.config.stable_duration_sec:
                        if (now - self._last_trigger_time) >= self.config.cooldown_sec:
                            if not self._looks_like_last_trigger(signature):
                                self._last_trigger_time = now
                                self._last_trigger_signature = signature.copy()
                                self._candidate_frame = frame_bgr.copy()
                                self._set_status("Card stable - triggered")
                                self.card_stable.emit(self._candidate_frame.copy())
                            else:
                                self._set_status("Same cared still in view")
                        self._change_armed = False
                        self._stable_since = None
            else:
                # Still moving, reset stabilization timer
                self._stable_since = now
                self._candidate_frame = frame_bgr.copy()
                self._set_status("Motion detected...")
            #print(f"change_score={change_score:.2f}, "f"stable_score={stable_score:.2f}, "f"stable_since={self._stable_since}")
        self._last_signatrue = signature
    
    def _compute_signature(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        if frame_bgr is None or frame_bgr.size == 0:
            return None
        
        h, w = frame_bgr.shape[:2]
        if h < 20 or w < 20:
            return None
        
        roi = self._center_crop(frame_bgr, self.config.roi_size)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (self.config.signature_size, self.config.signature_size), interpolation=cv2.INTER_AREA,)
        blurred = cv2.GaussianBlur(small, (5, 5), 0)
        return blurred.astype(np.float32)

    def _center_crop(self, frame: np.ndarray, size: int) -> np.ndarray:
        h, w = frame.shape[:2]
        crop_size = min(size, h, w)

        x1 = max(0, (w - crop_size) // 2)
        y1 = max(0, (h - crop_size) // 2)
        x2 = x1 + crop_size
        y2 = y1 + crop_size

        return frame[y1:y2, x1:x2]
    
    def _mean_abs_diff(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.mean(np.abs(a - b)))

    def _looks_like_last_trigger(self, signature: np.ndarray) -> bool:
        if self._last_trigger_signature is None:
            return False
        diff = self._mean_abs_diff(signature, self._last_trigger_signature)
        return diff <= self.config.stable_threshold

    def _set_status(self, text: str) -> None:
        if text != self._last_status:
            self._last_status = text
            self.status_changed.emit(text)

