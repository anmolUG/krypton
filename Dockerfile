# Use a full Python image to ensure better compatibility with OpenCV/ONNX
FROM python:3.11-bookworm

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenCV with a retry logic
RUN apt-get update || (sleep 5 && apt-get update) && apt-get install -y \
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
