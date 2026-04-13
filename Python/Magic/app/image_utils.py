from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np

# MTG cards are roughly 63x88mm so aspect ratio is 0.716
CARD_ASPECT_RATIO = 63.0 / 88.0 # width / height

def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order 4 points as: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4,2), dtype=np.float32)

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # bottom-right has largest sum

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right has smallest difference
    rect[3] = pts[np.argmax(diff)]  # bottom-left has largest difference

    return rect

def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Wrap the image as a top down view using the 4 corner points
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    max_width = int(max(width_top, width_bottom))

    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    max_height = int(max(height_left, height_right))

    max_width = max(1, max_width)
    max_height = max(1, max_height)

    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
    return warped

def resize_to_card_aspect(image: np.ndarray, target_height: int = 880, ) -> np.ndarray:
    """
    Resize warped image to a consistent MTG-like aspect ration
    """
    target_width = int(round(target_height * CARD_ASPECT_RATIO))
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)

def detect_card_contour(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """
    Detect most likely card contour in frame

    Return 4x2 float32 array of corner points if found, else None
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return None
    
    frame_h, frame_w = frame_bgr.shape[:2]

    # Center ROI: focus detection where the user is expected to place the card
    roi_w = int(frame_w * 0.72)
    roi_h = int(frame_h * 0.82)
    x0 = (frame_w - roi_w) // 2
    y0 = (frame_h - roi_h) // 2
    roi = frame_bgr[y0:y0+roi_h, x0:x0+roi_w]
    roi_area = float(roi_w * roi_h)
    roi_center = np.array([roi_w / 2.0, roi_h / 2.0], dtype=np.float32)

    #frame_area = float(h * w)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, None, iterations=2)
    edges = cv2.erode(edges, None, iterations=1)

    # Threshold
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    thresh = cv2.bitwise_not(thresh)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8), iterations=2)

    candidate_masks = [edges, thresh]

    # contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad = None
    best_score = -1e18

    for mask in candidate_masks:
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < roi_area * 0.03:
                continue

            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            if len(approx) !=4:
                continue

            if not cv2. isContourConvex(approx):
                continue

            pts = approx.reshape(4,2).astype(np.float32)

            rect = order_points(pts)
            (tl, tr, br, bl) = rect

            width_top = np.linalg.norm(tr - tl)
            width_bottom = np.linalg.norm(br - bl)
            height_left = np.linalg.norm(bl - tl)
            height_right = np.linalg.norm(br - tr)

            width = max(width_top, width_bottom)
            height = max(height_left, height_right)

            if width < 60 or height < 90:
                continue

            aspect = width / height if height > 0 else 0.0
            aspect_error = abs(aspect - CARD_ASPECT_RATIO)

            # contour center
            center = rect.mean(axis=0)
            center_dist = np.linalg.norm(center - roi_center)

            # Prefer larger contours with apsect ration closer to a card
            score = (area - (aspect_error * roi_area * 0.8) - (center_dist * 120.0))

            if score > best_score:
                best_score = score
                best_quad = rect
    if best_quad is None:
        return None

    # Convert ROI-local coordinates back to full-frame coordinates
    best_quad[:, 0] += x0
    best_quad[:, 1] += y0
    return best_quad

def extract_normalized_card(frame_bgr: np.ndarray, target_height: int = 880, ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Detect and extract normalized top-down card image.

    Returns: warped_card_bgr, contour_points
    """
    quad = detect_card_contour(frame_bgr)
    if quad is None: 
        return None, None
    
    warped = four_point_transform(frame_bgr, quad)

    # Normalize orientation
    h, w = warped.shape[:2]
    if h < w:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

    normalized = resize_to_card_aspect(warped, target_height=target_height)
    return normalized, quad

def draw_contour_overlay(frame_bgr: np.ndarray, quad: Optional[np.ndarray]) -> np.ndarray:
    """
    Return a copy of the frame with the detected contour drawn on it
    """
    output = frame_bgr.copy()
    if quad is None:
        return output
    
    pts = quad.astype(np.int32).reshape((-1,1,2))
    cv2.polylines(output, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
    return output

def save_image(image_bgr: np.ndarray, output_path: str | Path) -> Path:
    """
    Save a BGR image to disk
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ok = cv2.imwrite(str(output_path), image_bgr)
    if not ok:
        raise RuntimeError(f"Failed to save image to {output_path}")
    return output_path