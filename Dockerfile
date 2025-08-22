# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create necessary directories
RUN mkdir -p backend/data/processed backend/data/raw

# Set the working directory to backend since main_api.py is there
WORKDIR /app/backend

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]