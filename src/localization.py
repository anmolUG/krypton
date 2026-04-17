"""
Localization Module
===================
Estimates spatial location (row/column) from face bounding box positions
using k-means clustering on y-coordinates.
"""

import numpy as np
from sklearn.cluster import KMeans


def compute_face_centers(detections: list[dict]) -> list[tuple[float, float]]:
    """Compute face center (cx, cy) from bounding boxes.

    Args:
        detections: List of detection dicts with 'bbox' key [x1, y1, x2, y2].

    Returns:
        List of (cx, cy) tuples.
    """
    centers = []
    for det in detections:
        bbox = det["bbox"]
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        centers.append((cx, cy))
    return centers


def estimate_rows(face_centers: list[tuple[float, float]],
                  num_rows: int = 5,
                  auto_detect: bool = True) -> list[int]:
    """Estimate seating row for each face using k-means on y-coordinates.

    In a standard classroom photo taken from the front:
    - Lower y-values = closer to camera = front rows
    - Higher y-values = farther from camera = back rows

    Args:
        face_centers: List of (cx, cy) tuples.
        num_rows: Number of seating rows to estimate.
        auto_detect: If True, adjust num_rows based on actual face count.

    Returns:
        List of row numbers (1-indexed, 1 = front row).
    """
    if not face_centers:
        return []

    if len(face_centers) == 1:
        return [1]

    y_coords = np.array([c[1] for c in face_centers]).reshape(-1, 1)

    # Auto-adjust row count if needed
    actual_k = min(num_rows, len(face_centers))
    if auto_detect and len(face_centers) > 3:
        # Use a reasonable estimate: sqrt of face count, capped
        auto_k = max(2, min(int(np.sqrt(len(face_centers))), 8))
        actual_k = min(auto_k, len(face_centers))

    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(y_coords)

    # Sort cluster centers by y-value (ascending = front row)
    cluster_centers = kmeans.cluster_centers_.flatten()
    sorted_indices = np.argsort(cluster_centers)

    # Create mapping: original cluster label -> row number (1-indexed)
    label_to_row = {}
    for row_num, orig_label in enumerate(sorted_indices):
        label_to_row[orig_label] = row_num + 1

    row_assignments = [label_to_row[label] for label in labels]
    return row_assignments


def estimate_columns(face_centers: list[tuple[float, float]],
                     row_assignments: list[int]) -> list[int]:
    """Estimate column position within each row.

    Sorts faces left-to-right within each row based on x-coordinate.

    Args:
        face_centers: List of (cx, cy) tuples.
        row_assignments: List of row numbers (1-indexed).

    Returns:
        List of column numbers (1-indexed, 1 = leftmost).
    """
    if not face_centers:
        return []

    columns = [0] * len(face_centers)

    # Group faces by row
    rows = {}
    for idx, (center, row) in enumerate(zip(face_centers, row_assignments)):
        if row not in rows:
            rows[row] = []
        rows[row].append((idx, center[0]))  # (original_index, x_coord)

    # Sort within each row by x-coordinate
    for row, faces in rows.items():
        faces.sort(key=lambda x: x[1])  # Sort by x
        for col_num, (orig_idx, _) in enumerate(faces):
            columns[orig_idx] = col_num + 1

    return columns


def assign_locations(detections: list[dict], config: dict = None) -> list[dict]:
    """Assign spatial location to each detected face.

    Adds 'location' dict to each detection with:
        - face_center: (cx, cy)
        - row: estimated row number (1 = front)
        - column: estimated column number (1 = leftmost)

    Args:
        detections: List of detection dicts.
        config: Configuration dict.

    Returns:
        Updated detections with 'location' key.
    """
    if not detections:
        return detections

    config = config or {}
    loc_cfg = config.get("localization", {})
    num_rows = loc_cfg.get("num_rows", 5)
    auto_detect = loc_cfg.get("auto_detect_rows", True)

    # Compute centers
    face_centers = compute_face_centers(detections)

    # Estimate rows and columns
    row_assignments = estimate_rows(face_centers, num_rows, auto_detect)
    col_assignments = estimate_columns(face_centers, row_assignments)

    # Attach location info
    for i, det in enumerate(detections):
        det["location"] = {
            "face_center": face_centers[i],
            "row": row_assignments[i],
            "column": col_assignments[i],
        }

    return detections
