# Dockerfile for AI Tutorial Generator

# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCLING_OUTPUT_DIR=/app/docling_output \
    FLASK_ENV=production \
    FLASK_APP=app.py

# Create working directory
WORKDIR /app

# Install OS-level dependencies for Docling and PDF support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      poppler-utils \
      ghostscript \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure Docling output directory exists
RUN mkdir -p ${DOCLING_OUTPUT_DIR}

# Expose the port the Flask app runs on
EXPOSE 8080

# Default command: launch the Flask web server
CMD ["python", "app.py"]
