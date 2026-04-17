"""
Visualization Module
====================
Draws annotated bounding boxes with name, confidence, and row/column
overlays on the classroom image.
"""

import cv2
import numpy as np


# Professional Monochrome defaults (BGR)
COLOR_HIGH = (255, 255, 255)       # Solid White
COLOR_TENTATIVE = (180, 180, 180)  # Light Gray
COLOR_UNKNOWN = (80, 80, 80)       # Dark Gray
COLOR_AMBIGUOUS = (120, 120, 120)  # Medium Gray


def get_color_for_status(status: str, config: dict = None) -> tuple:
    """Get BGR color for a match status."""
    if config:
        vis_cfg = config.get("visualization", {}).get("colors", {})
        if status == "HIGH_CONFIDENCE" and "high_confidence" in vis_cfg:
            return tuple(vis_cfg["high_confidence"])
        if status == "TENTATIVE" and "tentative" in vis_cfg:
            return tuple(vis_cfg["tentative"])
        if status == "UNKNOWN" and "unknown" in vis_cfg:
            return tuple(vis_cfg["unknown"])

    color_map = {
        "HIGH_CONFIDENCE": COLOR_HIGH,
        "TENTATIVE": COLOR_TENTATIVE,
        "AMBIGUOUS": COLOR_AMBIGUOUS,
        "UNKNOWN": COLOR_UNKNOWN,
    }
    return color_map.get(status, COLOR_UNKNOWN)


def draw_results(image: np.ndarray, results: list[dict],
                 config: dict = None) -> np.ndarray:
    """Draw annotated bounding boxes on the classroom image.

    Args:
        image: BGR image (will be copied, not modified in place).
        results: List of per-face result dicts with 'detection', 'match', 'location' keys.
        config: Configuration dict.

    Returns:
        Annotated BGR image.
    """
    annotated = image.copy()
    config = config or {}
    vis_cfg = config.get("visualization", {})
    thickness = vis_cfg.get("bbox_thickness", 2)
    font_scale = vis_cfg.get("font_scale", 0.5)

    for res in results:
        det = res.get("detection", {})
        match = res.get("match", {})
        location = res.get("location", {})

        bbox = det.get("bbox")
        if bbox is None:
            continue

        x1, y1, x2, y2 = bbox
        status = match.get("status", "UNKNOWN")
        color = get_color_for_status(status, config)

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        # Build label text
        name = match.get("matched_name")
        score = match.get("top1_score", 0.0)
        row = location.get("row", "?")
        col = location.get("column", "?")

        if name:
            label = f"{name} ({score:.2f})"
        else:
            label = f"Unknown ({score:.2f})"

        location_label = f"R{row}C{col}"

        # Draw label background
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, 1)

        # Name label above bbox
        label_y = max(y1 - 5, th + 5)
        cv2.rectangle(annotated, (x1, label_y - th - 5), (x1 + tw + 4, label_y + 2), color, -1)
        cv2.putText(annotated, label, (x1 + 2, label_y - 2), font, font_scale,
                    (255, 255, 255), 1, cv2.LINE_AA)

        # Location label below bbox
        (tw2, th2), _ = cv2.getTextSize(location_label, font, font_scale * 0.8, 1)
        loc_y = min(y2 + th2 + 5, annotated.shape[0] - 5)
        cv2.putText(annotated, location_label, (x1, loc_y), font, font_scale * 0.8,
                    color, 1, cv2.LINE_AA)

    return annotated


def draw_attendance_summary(image: np.ndarray, attendance: dict) -> np.ndarray:
    """Draw a summary box on the image with attendance counts.

    Args:
        image: Annotated BGR image.
        attendance: Attendance dict from generate_attendance().

    Returns:
        Image with summary overlay.
    """
    annotated = image.copy()
    summary = attendance.get("summary", {})

    lines = [
        f"Detected: {summary.get('total_detected_faces', 0)}",
        f"Present: {summary.get('present_count', 0)}/{summary.get('total_enrolled', 0)}",
        f"High Confidence: {summary.get('high_confidence_count', 0)}",
        f"Tentative: {summary.get('tentative_count', 0)}",
        f"Unknown: {summary.get('unknown_faces_count', 0)}",
    ]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    padding = 10
    line_height = 25

    # Background box
    box_h = padding * 2 + line_height * len(lines)
    box_w = 280
    overlay = annotated.copy()
    cv2.rectangle(overlay, (5, 5), (5 + box_w, 5 + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

    # Text
    for i, line in enumerate(lines):
        y = padding + 20 + i * line_height
        cv2.putText(annotated, line, (padding + 5, y), font, font_scale,
                    (255, 255, 255), 1, cv2.LINE_AA)

    return annotated
