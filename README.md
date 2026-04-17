# Classroom AI Attendance System

A high-performance attendance tracking system utilizing deep learning for face detection, recognition, and analytics.

## Features
- **Face Recognition**: Powered by InsightFace (Buffalo_L) for high accuracy.
- **Analytics Dashboard**: Real-time insights into student attendance and engagement.
- **Scalable Backend**: Python-based processing with MongoDB for persistent storage.
- **Modern Frontend**: Next.js 15+ interface with a premium, responsive design.

---

## Tech Stack
- **Backend**: Python 3.10+, FastAPI/Gradio, OpenCV, ONNX Runtime, Faiss.
- **Frontend**: Next.js (TypeScript), Tailwind CSS.
- **Database**: MongoDB.

---

## Setup Instructions

### 1. Prerequisites
- Python 3.10 or higher.
- Node.js 18 or higher.
- MongoDB instance (local or Atlas).

### 2. Backend Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **Download Models**:
   The system requires the `buffalo_l` insightface models. These are excluded from the repository due to size. The system will attempt to download them automatically on first run, or you can manually place them in the `models/` directory.

### 3. Frontend Setup
1. Navigate to the web directory:
   ```bash
   cd web
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure environment:
   Create a `.env.local` file (copy from `.env.example` if available) and add your `MONGODB_URI` and `NEXTAUTH_SECRET`.
4. Run the development server:
   ```bash
   npm run dev
   ```

### 4. Running the System
You can use the provided `run.bat` (Windows) to start the backend application quickly.

---

##  Security
Before pushing to production/public, ensure that:
1. `.env` and `.env.local` are in your `.gitignore`.
2. No API keys or database connection strings are hardcoded in the source.


