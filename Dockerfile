# Multi-stage build for Atlas OS
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy minimal files for build
COPY pyproject.toml README.md ./
COPY src ./src

# Build the wheel
RUN pip install --upgrade pip hatchling && \
    python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 atlas

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*.whl && rm -rf /wheels

# Copy config and data directories
COPY --chown=atlas:atlas configs /app/configs

# Create data, models, and plugins directories
RUN mkdir -p /app/data /app/models /app/plugins && chown -R atlas:atlas /app/data /app/models /app/plugins

# Switch to non-root user
USER atlas

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; import httpx; httpx.get('http://127.0.0.1:8000/', timeout=5)" || exit 1

# Run the API server
CMD ["python", "-m", "atlas.api.server"]
