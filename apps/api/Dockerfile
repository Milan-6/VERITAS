# ==============================================================================
# VERITAS Backend API - Hugging Face Spaces Dockerfile
# Base: Python 3.10 Slim
# Exposes Port: 7860
# Non-Root Execution: User ID 1000 (user)
# ==============================================================================

FROM python:3.10-slim

# Install system dependencies required for building C extensions, PDF processing, and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user 'user' with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user

# Set environment variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    DATABASE_URL=sqlite:////home/user/app/veritas.db \
    QDRANT_LOCAL_PATH=/home/user/app/data/qdrant \
    VERITAS_STORAGE_DIR=/home/user/app/uploads/documents

# Set working directory
WORKDIR /home/user/app

# Copy requirements file first for layer caching
COPY --chown=user:user requirements.txt .

# Switch to non-root user
USER user

# Install Python dependencies as non-root user
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application source code
COPY --chown=user:user . /home/user/app

# Ensure persistent directories exist and are writable by non-root user
RUN mkdir -p /home/user/app/uploads/documents /home/user/app/data/qdrant

# Expose Hugging Face default port 7860
EXPOSE 7860

# Start FastAPI server on port 7860 using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
