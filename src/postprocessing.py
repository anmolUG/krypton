"""
Postprocessing Module
=====================
Duplicate suppression (one-student-one-face constraint),
confidence filtering, and structured output generation.
"""

import json
import numpy as np
from datetime import datetime


def suppress_duplicates(results: list[dict]) -> list[dict]:
    """Enforce one-student-one-face constraint.

    If two detected faces match the same enrolled student,
    keep only the one with the higher similarity score.
    The lower-scoring duplicate is reclassified as UNKNOWN.

    Args:
        results: List of result dicts with 'match' and 'detection' keys.

    Returns:
        Updated results with duplicates suppressed.
    """
    # Group by matched student ID
    id_to_indices = {}
    for idx, res in enumerate(results):
        match = res.get("match", {})
        student_id = match.get("matched_id")
        if student_id is not None:
            if student_id not in id_to_indices:
                id_to_indices[student_id] = []
            id_to_indices[student_id].append((idx, match.get("top1_score", 0.0)))

    # For each student, keep only the best match
    for student_id, entries in id_to_indices.items():
        if len(entries) > 1:
            # Sort by score descending
            entries.sort(key=lambda x: x[1], reverse=True)
            # Keep the first (highest score), suppress the rest
            for idx, score in entries[1:]:
                results[idx]["match"] = {
                    "status": "UNKNOWN",
                    "matched_id": None,
                    "matched_name": None,
                    "top1_score": score,
                    "top_k_results": results[idx]["match"].get("top_k_results", []),
                    "suppressed_as_duplicate": True,
                    "original_match_id": student_id,
                }

    return results


def generate_attendance(results: list[dict],
                        enrolled_ids: list[str],
                        enrolled_names: list[str]) -> dict:
    """Generate structured attendance record.

    Args:
        results: List of per-face result dicts.
        enrolled_ids: List of all enrolled student IDs.
        enrolled_names: List of all enrolled student names.

    Returns:
        Attendance dict with:
            - timestamp
            - summary counts
            - per-student attendance list
            - identified faces
            - unidentified faces
    """
    # Build sets of identified students
    identified = {}
    for res in results:
        match = res.get("match", {})
        student_id = match.get("matched_id")
        if student_id is not None:
            status = match.get("status", "UNKNOWN")
            if status in ("HIGH_CONFIDENCE", "TENTATIVE", "AMBIGUOUS"):
                identified[student_id] = {
                    "name": match.get("matched_name"),
                    "confidence": match.get("top1_score", 0.0),
                    "status": status,
                    "bbox": res.get("detection", {}).get("bbox"),
                    "location": res.get("location", {}),
                }

    # Build attendance list
    attendance = []
    for sid, sname in zip(enrolled_ids, enrolled_names):
        if sid in identified:
            info = identified[sid]
            attendance.append({
                "student_id": sid,
                "student_name": sname,
                "present": True,
                "confidence": info["confidence"],
                "status": info["status"],
                "bbox": info["bbox"],
                "row": info["location"].get("row"),
                "column": info["location"].get("column"),
            })
        else:
            attendance.append({
                "student_id": sid,
                "student_name": sname,
                "present": False,
                "confidence": 0.0,
                "status": "ABSENT",
                "bbox": None,
                "row": None,
                "column": None,
            })

    # Unidentified faces
    unidentified = []
    unknown_count = 0
    for res in results:
        match = res.get("match", {})
        if match.get("matched_id") is None:
            unknown_count += 1
            unidentified.append({
                "label": f"UNKNOWN_{unknown_count:03d}",
                "bbox": res.get("detection", {}).get("bbox"),
                "best_match_score": match.get("top1_score", 0.0),
                "location": res.get("location", {}),
                "was_duplicate": match.get("suppressed_as_duplicate", False),
            })

    present_count = sum(1 for a in attendance if a["present"])
    absent_count = sum(1 for a in attendance if not a["present"])
    high_conf = sum(1 for a in attendance if a["status"] == "HIGH_CONFIDENCE")
    tentative = sum(1 for a in attendance if a["status"] in ("TENTATIVE", "AMBIGUOUS"))

    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_enrolled": len(enrolled_ids),
            "total_detected_faces": len(results),
            "present_count": present_count,
            "absent_count": absent_count,
            "high_confidence_count": high_conf,
            "tentative_count": tentative,
            "unknown_faces_count": unknown_count,
        },
        "attendance": attendance,
        "unidentified_faces": unidentified,
    }


def save_attendance(attendance: dict, output_path: str):
    """Save attendance record as JSON."""
    with open(output_path, "w") as f:
        json.dump(attendance, f, indent=2, default=str)
