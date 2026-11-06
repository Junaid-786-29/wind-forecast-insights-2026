# ==============================================================================
# WindForecast Analytics - FastAPI Backend Dockerfile
# Base Image: Python 3.13 Slim (lightweight, secure Linux Debian-based image)
# Production Ready for Docker Compose and Cloud Hosting (Render / AWS / GCP)
# ==============================================================================

FROM python:3.13-slim AS runner

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies if required and update pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY main.py schemas.py ./
COPY app/ ./app/
COPY tests/ ./tests/

# Create a non-root system user for security
RUN useradd -u 1001 -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose backend service port (default 8000, dynamically mapped on Render)
EXPOSE 8000

# Container healthcheck querying /api/v1/health using dynamic PORT environment variable
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; port = os.getenv('PORT', '8000'); exit(0 if urllib.request.urlopen(f'http://localhost:{port}/api/v1/health').getcode() == 200 else 1)"

# Start Uvicorn ASGI server binding to 0.0.0.0 and supporting dynamic PORT (e.g. Render)
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
