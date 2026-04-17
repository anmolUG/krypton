"""
Pipeline Orchestrator
=====================
End-to-end pipeline: chains all modules from raw image to final
attendance output. Single entry point for the entire system.
"""

import cv2
import numpy as np
from pathlib import Path

from .detection import FaceDetector, load_config, preprocess_image
from .embedding import FaceEmbedder
from .matching import GalleryMatcher
from .enrollment import EnrollmentManager
from .localization import assign_locations
from .postprocessing import suppress_duplicates, generate_attendance, save_attendance
from .visualization import draw_results, draw_attendance_summary
from .database import MongoManager


class AttendancePipeline:
    """End-to-end classroom attendance pipeline.

    Usage:
        pipeline = AttendancePipeline()
        pipeline.load_gallery("data/gallery")
        result = pipeline.process_image("classroom_photo.jpg")
    """

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.detector = FaceDetector(self.config)
        self.embedder = FaceEmbedder(config=self.config)
        self.matcher = GalleryMatcher(self.config)
        self.db = MongoManager(self.config) if self.config.get("mongodb") else None
        self._gallery_loaded = False

    def load_gallery(self, gallery_dir: str = None):
        """Load pre-built gallery from disk."""
        if gallery_dir is None:
            gallery_dir = self.config.get("paths", {}).get("gallery_dir", "data/gallery")
        self.matcher.load_gallery(gallery_dir)
        self._gallery_loaded = True

    def set_matcher(self, matcher: GalleryMatcher):
        """Set an externally configured matcher (e.g., from EnrollmentManager)."""
        self.matcher = matcher
        self._gallery_loaded = (matcher.index is not None and matcher.index.ntotal > 0)

    def process_image(self, image_path: str = None,
                      image: np.ndarray = None) -> dict:
        """Process a single classroom image through the full pipeline.

        Args:
            image_path: Path to the classroom photo (BGR).
            image: BGR numpy array (alternative to path).

        Returns:
            Dict with:
                - detections: list of per-face detection results
                - results: list of per-face results with match + location
                - attendance: structured attendance record
                - annotated_image: BGR image with overlays
                - raw_image: original image
        """
        # --- Step 1: Load Image ---
        if image is None:
            if image_path is None:
                raise ValueError("Either image_path or image must be provided.")
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

        raw_image = image.copy()

        # --- Step 2: Detect Faces (includes preprocessing) ---
        detections, preprocessed, scale = self.detector.detect_with_preprocessing(image)

        if not detections:
            return self._empty_result(raw_image)

        # --- Step 3: Extract Embeddings ---
        # InsightFace's FaceAnalysis computes embeddings during detection.
        # We just need to ensure they are L2-normalized.
        for det in detections:
            emb = det.get("embedding")
            if emb is not None:
                emb = np.array(emb, dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 1e-10:
                    det["embedding"] = emb / norm
                else:
                    det["embedding"] = None

        # --- Step 4: Match Against Gallery ---
        if not self._gallery_loaded:
            # No gallery loaded — all faces are UNKNOWN
            match_results = [{"status": "UNKNOWN", "matched_id": None,
                              "matched_name": None, "top1_score": 0.0,
                              "top_k_results": []}
                             for _ in detections]
        else:
            embeddings = [det.get("embedding") for det in detections]
            match_results = self.matcher.match_batch(embeddings)

        # --- Step 5: Build Combined Results ---
        results = []
        for det, match in zip(detections, match_results):
            results.append({
                "detection": {
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                    "face_size": det["face_size"],
                },
                "match": match,
            })

        # --- Step 6: Duplicate Suppression ---
        results = suppress_duplicates(results)

        # --- Step 7: Location Assignment ---
        # We need detection dicts for the localizer
        det_for_loc = [{"bbox": r["detection"]["bbox"]} for r in results]
        det_for_loc = assign_locations(det_for_loc, self.config)

        for i, res in enumerate(results):
            res["location"] = det_for_loc[i].get("location", {})

        # --- Step 8: Generate Attendance Record ---
        attendance = generate_attendance(
            results,
            enrolled_ids=self.matcher.gallery_ids,
            enrolled_names=self.matcher.gallery_names,
        )

        # --- Step 9: Visualize ---
        annotated = draw_results(raw_image, results, self.config)
        annotated = draw_attendance_summary(annotated, attendance)

        return {
            "num_detected": len(detections),
            "results": results,
            "attendance": attendance,
            "annotated_image": annotated,
            "raw_image": raw_image,
        }

    def _empty_result(self, raw_image: np.ndarray) -> dict:
        """Return an empty result when no faces are detected."""
        enrolled_ids = self.matcher.gallery_ids if self._gallery_loaded else []
        enrolled_names = self.matcher.gallery_names if self._gallery_loaded else []

        attendance = generate_attendance([], enrolled_ids, enrolled_names)

        return {
            "num_detected": 0,
            "results": [],
            "attendance": attendance,
            "annotated_image": raw_image.copy(),
            "raw_image": raw_image,
        }

    def process_and_save(self, image_path: str, output_dir: str = None) -> dict:
        """Process an image and save annotated image + attendance JSON.

        Args:
            image_path: Path to the classroom photo.
            output_dir: Directory to save outputs. Defaults to config path.

        Returns:
            Same as process_image() plus output file paths.
        """
        if output_dir is None:
            output_dir = self.config.get("paths", {}).get("output_dir", "data/output")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Process
        result = self.process_image(image_path=image_path)

        # Save annotated image
        img_name = Path(image_path).stem
        annotated_path = str(output_path / f"{img_name}_annotated.jpg")
        cv2.imwrite(annotated_path, result["annotated_image"])

        # Save attendance JSON
        json_path = str(output_path / f"{img_name}_attendance.json")
        save_attendance(result["attendance"], json_path)

        result["annotated_image_path"] = annotated_path
        result["attendance_json_path"] = json_path

        # Database Storage
        if self.db:
            raw_id = self.db.save_image(result["raw_image"], f"{img_name}_raw.jpg", {"type": "classroom_raw", "source": image_path})
            ann_id = self.db.save_image(result["annotated_image"], f"{img_name}_annotated.jpg", {"type": "classroom_annotated", "source": image_path})
            result["mongodb_ids"] = {"raw": str(raw_id), "annotated": str(ann_id)}

        return result
