"""
Matching Module
===============
FAISS-based gallery matching with two-threshold decision logic.
Handles identity matching, ambiguity detection, and score-based decisions.
"""

import numpy as np
import faiss
import pickle
from pathlib import Path


class GalleryMatcher:
    """Matches probe face embeddings against an enrolled gallery using FAISS.

    The gallery is a FAISS IndexFlatIP (inner product = cosine similarity
    for L2-normalized vectors). Each gallery entry is a centroid embedding
    for one enrolled student.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        match_cfg = self.config.get("matching", {})
        self.tau_high = match_cfg.get("tau_high", 0.45)
        self.tau_low = match_cfg.get("tau_low", 0.30)
        self.ambiguity_margin = match_cfg.get("ambiguity_margin", 0.05)
        self.top_k = match_cfg.get("top_k", 3)

        self.index = None
        self.gallery_ids = []     # student_id per gallery entry
        self.gallery_names = []   # student_name per gallery entry

    def build_index(self, gallery: dict[str, dict]):
        """Build FAISS index from gallery data.

        Args:
            gallery: Dict mapping student_id to:
                {
                    "name": str,
                    "centroid": np.ndarray (512-d)
                }
        """
        embeddings = []
        self.gallery_ids = []
        self.gallery_names = []

        for student_id, data in gallery.items():
            centroid = data["centroid"]
            if centroid is not None:
                embeddings.append(centroid.astype(np.float32))
                self.gallery_ids.append(student_id)
                self.gallery_names.append(data["name"])

        if not embeddings:
            raise ValueError("No valid embeddings in gallery.")

        emb_matrix = np.stack(embeddings, axis=0)  # (N_gallery, 512)
        dim = emb_matrix.shape[1]

        # IndexFlatIP computes inner product (= cosine similarity for L2-normalized vectors)
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(emb_matrix)

    def save_gallery(self, gallery_dir: str):
        """Save the FAISS index and metadata to disk."""
        gallery_path = Path(gallery_dir)
        gallery_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(gallery_path / "gallery.index"))

        # Save metadata
        metadata = {
            "gallery_ids": self.gallery_ids,
            "gallery_names": self.gallery_names,
        }
        with open(gallery_path / "gallery_meta.pkl", "wb") as f:
            pickle.dump(metadata, f)

    def load_gallery(self, gallery_dir: str):
        """Load the FAISS index and metadata from disk."""
        gallery_path = Path(gallery_dir)

        self.index = faiss.read_index(str(gallery_path / "gallery.index"))

        with open(gallery_path / "gallery_meta.pkl", "rb") as f:
            metadata = pickle.load(f)

        self.gallery_ids = metadata["gallery_ids"]
        self.gallery_names = metadata["gallery_names"]

    def match(self, probe_embedding: np.ndarray) -> dict:
        """Match a single probe embedding against the gallery.

        Args:
            probe_embedding: 512-d L2-normalized embedding.

        Returns:
            Dict with match results:
                - status: "HIGH_CONFIDENCE" | "TENTATIVE" | "UNKNOWN" | "AMBIGUOUS"
                - matched_id: student_id or None
                - matched_name: student_name or None
                - top1_score: similarity score of best match
                - top_k_results: list of (student_id, student_name, score)
        """
        if self.index is None or self.index.ntotal == 0:
            return {
                "status": "UNKNOWN",
                "matched_id": None,
                "matched_name": None,
                "top1_score": 0.0,
                "top_k_results": [],
            }

        # Query FAISS
        query = probe_embedding.reshape(1, -1).astype(np.float32)
        k = min(self.top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        scores = scores[0]    # (top_k,)
        indices = indices[0]  # (top_k,)

        # Build top-k results
        top_k_results = []
        for i in range(k):
            idx = int(indices[i])
            if idx >= 0:
                top_k_results.append({
                    "student_id": self.gallery_ids[idx],
                    "student_name": self.gallery_names[idx],
                    "score": float(scores[i]),
                })

        if not top_k_results:
            return {
                "status": "UNKNOWN",
                "matched_id": None,
                "matched_name": None,
                "top1_score": 0.0,
                "top_k_results": [],
            }

        top1 = top_k_results[0]
        top1_score = top1["score"]

        # Decision logic
        # Check for ambiguity: top-1 and top-2 scores are very close
        status = "UNKNOWN"
        if len(top_k_results) >= 2:
            score_gap = top1_score - top_k_results[1]["score"]
            if top1_score >= self.tau_low and score_gap < self.ambiguity_margin:
                status = "AMBIGUOUS"
            elif top1_score >= self.tau_high:
                status = "HIGH_CONFIDENCE"
            elif top1_score >= self.tau_low:
                status = "TENTATIVE"
        else:
            if top1_score >= self.tau_high:
                status = "HIGH_CONFIDENCE"
            elif top1_score >= self.tau_low:
                status = "TENTATIVE"

        matched_id = top1["student_id"] if status != "UNKNOWN" else None
        matched_name = top1["student_name"] if status != "UNKNOWN" else None

        return {
            "status": status,
            "matched_id": matched_id,
            "matched_name": matched_name,
            "top1_score": top1_score,
            "top_k_results": top_k_results,
        }

    def match_batch(self, probe_embeddings: list[np.ndarray]) -> list[dict]:
        """Match multiple probe embeddings against the gallery.

        Args:
            probe_embeddings: List of 512-d L2-normalized embeddings.

        Returns:
            List of match result dicts (same format as match()).
        """
        results = []
        for emb in probe_embeddings:
            if emb is not None:
                results.append(self.match(emb))
            else:
                results.append({
                    "status": "UNKNOWN",
                    "matched_id": None,
                    "matched_name": None,
                    "top1_score": 0.0,
                    "top_k_results": [],
                })
        return results
