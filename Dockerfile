# DevMatrix - Multi-stage Dockerfile for Production Deployment
# Optimized for size, security, and performance

# =============================================================================
# Stage 1: Builder - Install dependencies and build wheels
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt requirements-dev.txt ./

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn[standard] gunicorn

# =============================================================================
# Stage 2: UI Builder - Build React frontend
# =============================================================================
FROM node:20-alpine as ui-builder

WORKDIR /ui

# Copy UI package files
COPY src/ui/package.json src/ui/package-lock.json* ./

# Install dependencies
RUN npm ci --only=production

# Copy UI source
COPY src/ui/ ./

# Build for production
RUN npm run build

# =============================================================================
# Stage 3: Development - Full development environment
# =============================================================================
FROM python:3.11-slim as development

# Install runtime and development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    git \
    curl \
    vim \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY templates/ ./templates/
COPY alembic.ini pyproject.toml ./

# Create necessary directories
RUN mkdir -p /app/workspace /app/logs /app/data

# Set environment variables
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=development

EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# =============================================================================
# Stage 4: Production - Minimal secure production image
# =============================================================================
FROM python:3.11-slim as production

# Set metadata
LABEL maintainer="DevMatrix Team <team@devmatrix.example.com>" \
      description="DevMatrix Multi-Agent AI Development Environment" \
      version="0.1.0" \
      org.opencontainers.image.source="https://github.com/yourusername/devmatrix"

# Create non-root user and group
RUN groupadd -r devmatrix && \
    useradd -r -g devmatrix -u 1000 -m -s /sbin/nologin devmatrix

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code with correct ownership
COPY --chown=devmatrix:devmatrix src/ ./src/
COPY --chown=devmatrix:devmatrix alembic/ ./alembic/
COPY --chown=devmatrix:devmatrix templates/ ./templates/
COPY --chown=devmatrix:devmatrix alembic.ini pyproject.toml ./

# Copy built UI from ui-builder stage
COPY --from=ui-builder --chown=devmatrix:devmatrix /ui/dist ./src/api/static

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/data /app/workspace && \
    chown -R devmatrix:devmatrix /app

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    PORT=8000 \
    WORKERS=4

# Switch to non-root user
USER devmatrix

# Health check with proper endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health/live || exit 1

# Expose port
EXPOSE 8000

# Use gunicorn with uvicorn workers for production
CMD exec gunicorn src.api.main:app \
    --bind 0.0.0.0:${PORT} \
    --workers ${WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
