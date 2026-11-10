# ==============================================================================
# VERITAS Backend API & Background Worker
# Multi-Stage Dockerfile (Python 3.12-slim)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies for compiling Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into /root/.local
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Minimal Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime libraries (libpq for PostgreSQL, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Ensure executables in /root/.local/bin are in PATH
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Copy application source code
COPY . /app

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Create persistent storage directories for uploads and vectors
RUN mkdir -p /app/uploads/documents /app/data/qdrant

# Expose API port
EXPOSE 8000

# Set entrypoint & default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["api"]
