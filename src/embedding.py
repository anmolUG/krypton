"""
Embedding Module
================
ArcFace embedding extraction via InsightFace's recognition model.
Handles batch processing and L2 normalization.
"""

import numpy as np


class FaceEmbedder:
    """Extracts 512-d ArcFace embeddings from aligned face chips.

    Uses InsightFace's bundled ArcFace-R100 model (loaded as part of the
    FaceAnalysis model pack). Can also be used standalone with the
    recognition model directly.
    """

    def __init__(self, detector_model=None, config: dict = None):
        """
        Args:
            detector_model: An initialized FaceDetector whose underlying
                InsightFace model already includes the recognition component.
                If None, embeddings must come from the detection results.
            config: Configuration dict.
        """
        self.detector_model = detector_model
        self.config = config or {}
        self.emb_cfg = self.config.get("embedding", {})
        self.embedding_dim = self.emb_cfg.get("embedding_dim", 512)

    def extract_single(self, aligned_face: np.ndarray) -> np.ndarray | None:
        """Extract embedding from a single aligned 112x112 face chip.

        When InsightFace's FaceAnalysis is used, embeddings are already
        computed during detection. This method is for cases where you
        have a standalone aligned face chip.

        Returns:
            512-d L2-normalized embedding vector, or None.
        """
        if aligned_face is None:
            return None

        if self.detector_model is not None and hasattr(self.detector_model, 'models'):
            rec_model = self.detector_model.models.get('recognition', None)
            if rec_model is not None:
                embedding = rec_model.get(aligned_face)
                return self._l2_normalize(embedding)

        return None

    def extract_from_detections(self, detections: list[dict]) -> list[dict]:
        """Extract or retrieve embeddings from detection results.

        InsightFace's FaceAnalysis computes embeddings during the .get() call,
        so they are already available in the detection results. This method
        retrieves them and ensures L2 normalization.

        Args:
            detections: List of detection dicts (with 'embedding' key from detector).

        Returns:
            Updated list of dicts with 'embedding' key containing 512-d vectors.
        """
        for det in detections:
            emb = det.get("embedding")
            if emb is not None:
                det["embedding"] = self._l2_normalize(np.array(emb))
            else:
                det["embedding"] = None

        return detections

    def compute_centroid(self, embeddings: list[np.ndarray]) -> np.ndarray:
        """Compute centroid embedding from multiple embeddings.

        Average all embeddings and L2-normalize the result.
        This produces a robust identity representation that is
        less sensitive to per-image noise.

        Args:
            embeddings: List of 512-d embedding vectors.

        Returns:
            512-d L2-normalized centroid embedding.
        """
        if not embeddings:
            return None

        # Filter out None values
        valid = [e for e in embeddings if e is not None]
        if not valid:
            return None

        stacked = np.stack(valid, axis=0)  # (N, 512)
        centroid = np.mean(stacked, axis=0)  # (512,)
        return self._l2_normalize(centroid)

    @staticmethod
    def _l2_normalize(embedding: np.ndarray) -> np.ndarray:
        """L2-normalize an embedding vector."""
        norm = np.linalg.norm(embedding)
        if norm < 1e-10:
            return embedding
        return embedding / norm

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two L2-normalized embeddings.
        For L2-normalized vectors, this is equivalent to dot product."""
        return float(np.dot(emb1, emb2))
