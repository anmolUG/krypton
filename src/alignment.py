"""
Face Alignment Module
=====================
Aligns detected faces to a canonical 112×112 template using
5-point landmark similarity transform.
"""

import cv2
import numpy as np
from skimage.transform import SimilarityTransform


# Standard InsightFace reference landmarks for 112x112 aligned face
REFERENCE_LANDMARKS_112 = np.array([
    [38.2946, 51.6963],   # left eye
    [73.5318, 51.5014],   # right eye
    [56.0252, 71.7366],   # nose tip
    [41.5493, 92.3655],   # left mouth corner
    [70.7299, 92.2041],   # right mouth corner
], dtype=np.float32)


def estimate_similarity_transform(src_landmarks: np.ndarray,
                                   dst_landmarks: np.ndarray) -> np.ndarray:
    """Estimate similarity transform (rotation + scale + translation)
    from source landmarks to destination landmarks.

    Returns:
        3x3 transformation matrix.
    """
    tform = SimilarityTransform()
    tform.estimate(src_landmarks, dst_landmarks)
    return tform.params[0:2, :]  # 2x3 affine matrix


def align_face(image: np.ndarray, landmarks: list | np.ndarray,
               output_size: tuple = (112, 112)) -> np.ndarray | None:
    """Align a face using 5-point landmarks to a canonical template.

    Args:
        image: Full BGR image.
        landmarks: 5x2 array/list of facial landmarks
                   [left_eye, right_eye, nose, left_mouth, right_mouth].
        output_size: Target size for the aligned face chip.

    Returns:
        Aligned face chip (112x112x3 BGR) or None if alignment fails.
    """
    if landmarks is None or len(landmarks) < 5:
        return None

    src = np.array(landmarks, dtype=np.float32)

    # Scale reference landmarks if output_size is not 112x112
    if output_size == (112, 112):
        dst = REFERENCE_LANDMARKS_112.copy()
    else:
        scale_x = output_size[0] / 112.0
        scale_y = output_size[1] / 112.0
        dst = REFERENCE_LANDMARKS_112.copy()
        dst[:, 0] *= scale_x
        dst[:, 1] *= scale_y

    # Estimate and apply the similarity transform
    M = estimate_similarity_transform(src, dst)
    aligned = cv2.warpAffine(
        image, M, output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )

    return aligned


def crop_face(image: np.ndarray, bbox: list, expand_ratio: float = 0.2) -> np.ndarray:
    """Crop a face from the image with optional bounding box expansion.

    Args:
        image: Full BGR image.
        bbox: [x1, y1, x2, y2] bounding box.
        expand_ratio: Fraction to expand the bbox on each side.

    Returns:
        Cropped face region.
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    bw = x2 - x1
    bh = y2 - y1

    # Expand
    x1 = max(0, int(x1 - bw * expand_ratio))
    y1 = max(0, int(y1 - bh * expand_ratio))
    x2 = min(w, int(x2 + bw * expand_ratio))
    y2 = min(h, int(y2 + bh * expand_ratio))

    return image[y1:y2, x1:x2].copy()


def align_faces_batch(image: np.ndarray, detections: list[dict],
                      output_size: tuple = (112, 112),
                      min_face_size: int = 20) -> list[dict]:
    """Align all detected faces, filtering by quality.

    Args:
        image: Full BGR image.
        detections: List of detection dicts from FaceDetector.
        output_size: Target aligned face chip size.
        min_face_size: Minimum face size to process.

    Returns:
        List of dicts with added 'aligned_face' key (or None if alignment failed).
    """
    results = []
    for det in detections:
        if det["face_size"] < min_face_size:
            continue

        aligned = align_face(image, det.get("landmarks"), output_size)
        raw_crop = crop_face(image, det["bbox"])

        entry = {
            **det,
            "aligned_face": aligned,
            "raw_crop": raw_crop,
        }
        results.append(entry)

    return results
