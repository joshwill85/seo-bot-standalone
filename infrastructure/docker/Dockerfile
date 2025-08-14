# Multi-stage build for SEO Bot application
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy frontend package files
COPY frontend/package*.json ./
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./
COPY frontend/tailwind.config.js ./
COPY frontend/postcss.config.js ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source code
COPY frontend/src/ ./src/
COPY frontend/index.html ./

# Build frontend
RUN npm run build

# Python backend stage
FROM python:3.9-slim AS backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy Python dependency files
COPY backend/pyproject.toml backend/poetry.lock ./

# Configure poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy Python source code
COPY backend/src/ ./src/

# Production stage
FROM python:3.9-slim AS production

WORKDIR /app

# Install system dependencies for production
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python environment from builder
COPY --from=backend-builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=backend-builder /app/src ./src/
COPY --from=frontend-builder /app/dist ./static/

# Copy configuration files
COPY backend/pyproject.toml ./
COPY docs/README.md ./
COPY LICENSE ./

# Create necessary directories
RUN mkdir -p logs data backups test_reports exports \
    && chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Start command
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]