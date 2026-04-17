"""
Enrollment Module
=================
Processes enrollment images per student, computes centroid embeddings,
and builds the FAISS gallery index.
"""

import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm

from .detection import FaceDetector, load_config
from .embedding import FaceEmbedder
from .matching import GalleryMatcher
from .database import MongoManager


class EnrollmentManager:
    """Manages student enrollment: processes reference images,
    computes centroid embeddings, and builds the gallery index."""

    def __init__(self, config: dict = None):
        if config is None:
            config = load_config()
        self.config = config
        self.detector = FaceDetector(config)
        self.embedder = FaceEmbedder(config=config)
        self.matcher = GalleryMatcher(config)
        self.db = MongoManager(config) if config.get("mongodb") else None
        self.gallery = {}  # student_id -> {name, centroid, num_images}

    def enroll_student(self, student_id: str, student_name: str,
                       image_paths: list[str] = None,
                       images: list[np.ndarray] = None) -> dict:
        """Enroll a single student from reference images.

        Detects the face in each reference image, extracts the embedding,
        and computes the centroid.

        Args:
            student_id: Unique identifier for the student.
            student_name: Display name.
            image_paths: List of file paths to reference images.
            images: List of BGR numpy arrays (alternative to paths).

        Returns:
            Dict with enrollment result:
                - success: bool
                - num_valid_images: int
                - message: str
        """
        embeddings = []

        # Load images
        imgs = []
        if image_paths:
            for path in image_paths:
                img = cv2.imread(str(path))
                if img is not None:
                    imgs.append(img)
        if images:
            imgs.extend(images)

        if not imgs:
            return {
                "success": False,
                "num_valid_images": 0,
                "message": f"No valid images found for {student_name}."
            }

        for img in imgs:
            # Detect faces — expect exactly one face in an enrollment photo
            detections = self.detector.detect(img)

            if len(detections) == 0:
                continue  # Skip images with no detected face

            # Use the most confident detection (should be the primary face)
            best_det = detections[0]
            emb = best_det.get("embedding")

            if emb is not None:
                emb = np.array(emb, dtype=np.float32)
                norm = np.linalg.norm(emb)
                if norm > 1e-10:
                    emb = emb / norm
                    embeddings.append(emb)

        if not embeddings:
            return {
                "success": False,
                "num_valid_images": 0,
                "message": f"Could not extract face embeddings for {student_name}."
            }

        # Compute centroid
        centroid = self.embedder.compute_centroid(embeddings)

        # Save to database if available
        if self.db and imgs:
            self.db.enroll_student_images(student_id, imgs)

        self.gallery[student_id] = {
            "name": student_name,
            "centroid": centroid,
            "num_images": len(embeddings),
        }

        return {
            "success": True,
            "num_valid_images": len(embeddings),
            "message": f"Enrolled {student_name} with {len(embeddings)} valid images."
        }

    def delete_student(self, student_id: str) -> dict:
        """Removes a student from the gallery and database."""
        # 1. Remove from local gallery dictionary (if it exists)
        if student_id in self.gallery:
            student_name = self.gallery[student_id]["name"]
            del self.gallery[student_id]
        else:
            student_name = student_id  # Fallback
            
        # Optional: Actually we can just rebuild the faiss index manually to be safe
        # if they aren't in self.gallery but ARE in FAISS.
        import numpy as np
        
        # 2. Remove from database if enabled
        if self.db:
            self.db.delete_student(student_id)
            
        # 3. Save gallery rebuilds the index from self.gallery
        self.save_gallery()
        
        return {"success": True, "message": f"Deleted {student_name} from gallery and database."}

    def enroll_from_directory(self, enrollment_dir: str) -> dict:
        """Enroll all students from a directory structure.

        Expected structure:
            enrollment_dir/
                StudentName_ID/
                    img1.jpg
                    img2.jpg
                    ...

        The subfolder name is used as both student_name and student_id.

        Returns:
            Summary dict with enrollment results.
        """
        enrollment_path = Path(enrollment_dir)
        if not enrollment_path.exists():
            return {"success": False, "message": f"Directory {enrollment_dir} not found."}

        results = []
        student_dirs = sorted([d for d in enrollment_path.iterdir() if d.is_dir()])

        for student_dir in tqdm(student_dirs, desc="Enrolling students"):
            student_name = student_dir.name
            student_id = student_name  # Use folder name as ID

            image_paths = sorted([
                str(f) for f in student_dir.iterdir()
                if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            ])

            result = self.enroll_student(student_id, student_name, image_paths=image_paths)
            results.append(result)

        # Build FAISS index
        if self.gallery:
            self.matcher.build_index(self.gallery)

        enrolled = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        return {
            "success": True,
            "total_students": len(student_dirs),
            "enrolled": enrolled,
            "failed": failed,
            "results": results,
        }

    def save_gallery(self, gallery_dir: str = None):
        """Save the gallery to disk."""
        if gallery_dir is None:
            gallery_dir = self.config.get("paths", {}).get("gallery_dir", "data/gallery")

        # Always ensure index is synced with current gallery before saving
        if self.gallery:
            self.matcher.build_index(self.gallery)
        else:
            # If gallery is empty (everyone deleted), we need to clear the matcher index too.
            import faiss
            self.matcher.index = faiss.IndexFlatIP(self.config.get("embedding", {}).get("embedding_dim", 512))
            self.matcher.gallery_ids = []
            self.matcher.gallery_names = []

        self.matcher.save_gallery(gallery_dir)
        
        # Save the dictionary state
        import pickle
        with open(Path(gallery_dir) / "gallery_dict.pkl", "wb") as f:
            pickle.dump(self.gallery, f)

    def load_gallery(self, gallery_dir: str = None):
        """Load a pre-built gallery from disk."""
        if gallery_dir is None:
            gallery_dir = self.config.get("paths", {}).get("gallery_dir", "data/gallery")
            
        self.matcher.load_gallery(gallery_dir)
        
        # Load the dictionary state if it exists
        import pickle
        dict_path = Path(gallery_dir) / "gallery_dict.pkl"
        if dict_path.exists():
            with open(dict_path, "rb") as f:
                self.gallery = pickle.load(f)
        else:
            # Fallback if dictionary wasn't saved previously (backward compat)
            print("Warning: gallery_dict.pkl not found. Delete operations may fail for older students.")
            self.gallery = {}

    def get_gallery_info(self) -> dict:
        """Get summary info about the current gallery."""
        return {
            "num_enrolled": len(self.gallery_ids),
            "student_names": list(self.gallery_names),
        }

    @property
    def gallery_ids(self):
        return self.matcher.gallery_ids

    @property
    def gallery_names(self):
        return self.matcher.gallery_names
