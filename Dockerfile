# Multi-stage Dockerfile for Shark Foraging Hotspot Prediction Server
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gfortran \
    libhdf5-dev \
    libnetcdf-dev \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
# Using -dev packages for guaranteed compatibility (adds ~50MB but ensures it works)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-dev \
    libnetcdf-dev \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Update PATH to include local Python packages
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY README.md .
COPY setup.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=False
ENV CACHE_DIR=/app/data_cache

# Create directory for data caching
RUN mkdir -p /app/data_cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Change to backend directory and run the application
WORKDIR /app/backend
CMD ["python", "main.py"]

