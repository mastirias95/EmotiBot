FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first (for better caching)
COPY ../shared-libs /app/shared-libs

# Install shared library dependencies
RUN pip install -r /app/shared-libs/requirements.txt

# Copy service requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 wsuser && chown -R wsuser:wsuser /app
USER wsuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

EXPOSE 8006

CMD ["python", "app.py"] 