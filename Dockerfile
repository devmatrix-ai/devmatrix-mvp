# Devmatrix - Multi-stage Dockerfile for FastAPI Application
# Python 3.12+ required

# Stage 1: Base image with dependencies
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Stage 2: Development image
FROM base as development

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml .

# Create workspace directory
RUN mkdir -p /app/workspace

# Expose FastAPI port
EXPOSE 8000

# Development command (with reload)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 3: Production image (future)
FROM base as production

# Copy requirements
COPY requirements.txt .

# Install only production dependencies (no dev tools)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-dev

# Copy application code only (no tests)
COPY src/ ./src/
COPY pyproject.toml .

# Create non-root user for security
RUN useradd -m -u 1000 devmatrix && \
    chown -R devmatrix:devmatrix /app

USER devmatrix

# Create workspace directory
RUN mkdir -p /app/workspace

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no reload, optimized)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
