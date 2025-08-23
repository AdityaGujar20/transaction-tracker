# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and clean up in same layer
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --compile -r requirements.txt \
    && pip cache purge

# Copy only necessary application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create necessary directories
RUN mkdir -p backend/data/processed backend/data/raw

# Set the working directory to backend since main_api.py is there
WORKDIR /app/backend

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]