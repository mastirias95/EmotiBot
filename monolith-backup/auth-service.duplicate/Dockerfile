FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first (for better caching)
COPY shared-libs /app/shared-libs

# Install shared library dependencies
RUN pip install -r /app/shared-libs/requirements.txt

# Copy service requirements and install
COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth-service/ .

# Create non-root user
RUN useradd -m -u 1000 authuser && chown -R authuser:authuser /app
USER authuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

EXPOSE 8002

CMD ["python", "app.py"] 