"""
Database Module (MongoDB)
=========================
Handles connection to MongoDB and image storage using GridFS.
Efficiently stores high-resolution classroom images and enrollment references.
"""

import cv2
import numpy as np
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from pathlib import Path
import datetime

class MongoManager:
    """Manages MongoDB connection and GridFS image storage."""

    def __init__(self, config: dict):
        self.config = config.get("mongodb", {})
        self.uri = self.config.get("uri", "mongodb://localhost:27017/")
        self.db_name = self.config.get("db_name", "classroom_analytics")
        
        # Connection
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
        
        # GridFS for large image storage
        self.fs = gridfs.GridFS(self.db)
        
        # Collections
        self.students = self.db["students"]       # Metadata about students
        self.sessions = self.db["sessions"]       # Metadata about video sessions
        self.detections = self.db["detections"]   # Frame-level metrics

    def save_image(self, image: np.ndarray, filename: str, metadata: dict = None) -> ObjectId:
        """Encodes and saves a numpy image to GridFS.
        
        Args:
            image: BGR numpy array.
            filename: Descriptive name for the file.
            metadata: Optional dict of attributes (e.g., student_id, frame_idx).
            
        Returns:
            ObjectId of the stored file.
        """
        success, encoded_img = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not success:
            raise ValueError("Could not encode image to JPEG.")
            
        file_id = self.fs.put(
            encoded_img.tobytes(),
            filename=filename,
            metadata=metadata,
            uploadDate=datetime.datetime.utcnow()
        )
        return file_id

    def get_image(self, file_id: ObjectId) -> np.ndarray:
        """Retrieves and decodes a numpy image from GridFS."""
        file_data = self.fs.get(file_id).read()
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image

    def enroll_student_images(self, student_id: str, images: list[np.ndarray]):
        """Saves enrollment images for a student and updates their record."""
        image_ids = []
        for i, img in enumerate(images):
            fname = f"enrollment_{student_id}_{i}.jpg"
            fid = self.save_image(img, fname, {"student_id": student_id, "type": "enrollment"})
            image_ids.append(fid)
            
        self.students.update_one(
            {"student_id": student_id},
            {
                "$set": {
                    "updated_at": datetime.datetime.utcnow(),
                    "enrollment_image_ids": image_ids
                },
                "$setOnInsert": {"created_at": datetime.datetime.utcnow()}
            },
            upsert=True
        )

    def delete_student(self, student_id: str):
        """Deletes a student record and their associated GridFS images."""
        record = self.students.find_one({"student_id": student_id})
        if record and record.get("enrollment_image_ids"):
            # Delete physical images from GridFS
            for img_id in record["enrollment_image_ids"]:
                try:
                    self.fs.delete(img_id)
                except Exception as e:
                    print(f"Error deleting image {img_id} from GridFS: {e}")
                    
        # Delete student metadata document
        self.students.delete_one({"student_id": student_id})

    def close(self):
        self.client.close()
