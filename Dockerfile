FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy model downloader and download model at build time
COPY download_model.py .
RUN python download_model.py

# Copy application code
COPY main.py .

# Set environment variables for PyTorch optimization
ENV OMP_NUM_THREADS=2
ENV KMP_BLOCKTIME=1
ENV KMP_AFFINITY=granularity=fine,compact,1,0

# Expose port
EXPOSE 8080

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
