import io
import cv2
import base64
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline import AttendancePipeline
from .enrollment import EnrollmentManager
from .detection import load_config

app = FastAPI(title="Krypton Research API", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
CONFIG = load_config()
pipeline = AttendancePipeline()
enrollment_manager = EnrollmentManager(CONFIG)

# Load existing students from disk so they survive server restarts
try:
    enrollment_manager.load_gallery()
    print("Gallery loaded successfully. Students enrolled:", len(enrollment_manager.matcher.gallery_ids))
except Exception as e:
    print(f"Skipping gallery load (it might be empty): {e}")

# Ensure gallery is shared
pipeline.set_matcher(enrollment_manager.matcher)

# --- Models ---
class DetectionResult(BaseModel):
    bbox: List[float]
    confidence: float
    face_size: int

class MatchResult(BaseModel):
    status: str
    matched_id: Optional[str]
    matched_name: Optional[str]
    top1_score: float

class AnalysisResponse(BaseModel):
    num_detected: int
    attendance_summary: dict
    annotated_image_base64: str
    results: List[dict]
    full_attendance: dict

# --- Helper ---
def decode_image(contents: bytes) -> np.ndarray:
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    return img

def encode_image(img: np.ndarray) -> str:
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

# --- Endpoints ---

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/v1/enroll")
async def enroll_student(
    student_name: str = Form(...),
    files: List[UploadFile] = File(...)
):
    student_id = student_name.replace(" ", "_").lower()
    images = []
    
    for file in files:
        contents = await file.read()
        images.append(decode_image(contents))
    
    result = enrollment_manager.enroll_student(student_id, student_name, images=images)
    
    if result["success"]:
        # Save to disk and build FAISS index
        enrollment_manager.save_gallery()
        # Re-sync pipeline matcher
        pipeline.set_matcher(enrollment_manager.matcher)
        return {"status": "success", "student_id": student_id, "message": result["message"]}
    else:
        raise HTTPException(status_code=500, detail=result["message"])

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_classroom(file: UploadFile = File(...)):
    contents = await file.read()
    img = decode_image(contents)
    
    # Run the pipeline
    result = pipeline.process_image(image=img)
    
    encoded_annotated = encode_image(result["annotated_image"])
    
    return {
        "num_detected": result["num_detected"],
        "attendance_summary": result["attendance"].get("summary", {}),
        "annotated_image_base64": encoded_annotated,
        "results": result["results"],
        "full_attendance": result["attendance"]
    }

@app.get("/api/v1/registry")
async def get_registry():
    """Return list of enrolled students along with their primary stored image."""
    students = []
    
    # We will use the MongoManager to fetch the avatar if it exists
    for sid, name in zip(enrollment_manager.matcher.gallery_ids, enrollment_manager.matcher.gallery_names):
        student_data = {"id": sid, "name": name, "avatar": None, "image_count": 0}
        
        if enrollment_manager.db:
            record = enrollment_manager.db.students.find_one({"student_id": sid})
            if record and record.get("enrollment_image_ids"):
                image_ids = record["enrollment_image_ids"]
                student_data["image_count"] = len(image_ids)
                
                # Fetch first image as avatar
                first_img_id = image_ids[0]
                try:
                    img_np = enrollment_manager.db.get_image(first_img_id)
                    student_data["avatar"] = encode_image(img_np)
                except Exception as e:
                    print(f"Error fetching image for {sid}:", e)
        
        students.append(student_data)
        
    return {"students": students, "total": len(students)}

@app.get("/api/v1/registry/{student_id}/images")
async def get_student_images(student_id: str):
    """Return all enrolled images for a specific student as base64 strings."""
    images = []
    if enrollment_manager.db:
        record = enrollment_manager.db.students.find_one({"student_id": student_id})
        if record and record.get("enrollment_image_ids"):
            for img_id in record["enrollment_image_ids"]:
                try:
                    img_np = enrollment_manager.db.get_image(img_id)
                    images.append(encode_image(img_np))
                except Exception as e:
                    print(f"Error fetching image {img_id} for {student_id}:", e)
    
    if not images:
        raise HTTPException(status_code=404, detail="No images found for this student.")
        
    return {"student_id": student_id, "images": images}

@app.delete("/api/v1/registry/{student_id}")
async def delete_student(student_id: str):
    """Delete a student from the gallery, FAISS index, and database."""
    res = enrollment_manager.delete_student(student_id)
    if res["success"]:
        # Re-sync pipeline matcher to drop the deleted embedding
        pipeline.set_matcher(enrollment_manager.matcher)
        return {"status": "success", "message": res["message"]}
    else:
        raise HTTPException(status_code=404, detail=res["message"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
