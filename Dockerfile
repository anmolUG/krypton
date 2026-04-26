# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies for OpenCV and ONNX
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY src/ ./src/
COPY configs/ ./configs/
COPY download_models.py .

# Pre-download models during build to keep the container ready
RUN python download_models.py

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "src.api"]
