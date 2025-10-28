# Uplifted Dockerfile
# Multi-stage build for production optimization
# Python 3.11+ required

# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e .

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim AS runtime

# Set labels
LABEL maintainer="Uplifted Team <team@uplifted.ai>"
LABEL description="Uplifted AI Agent System"
LABEL version="0.53.1"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UPLIFTED_HOME=/app \
    UPLIFTED_DATA=/data \
    UPLIFTED_CONFIG=/config \
    UPLIFTED_LOGS=/logs \
    UPLIFTED_PLUGINS=/plugins

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # System utilities
    curl \
    ca-certificates \
    # For pyautogui and GUI automation
    libx11-6 \
    libxtst6 \
    libxrandr2 \
    libxi6 \
    # For matplotlib
    libfreetype6 \
    libpng16-16 \
    # For mediapipe
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash uplifted && \
    mkdir -p $UPLIFTED_DATA $UPLIFTED_CONFIG $UPLIFTED_LOGS $UPLIFTED_PLUGINS && \
    chown -R uplifted:uplifted $UPLIFTED_DATA $UPLIFTED_CONFIG $UPLIFTED_LOGS $UPLIFTED_PLUGINS

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=uplifted:uplifted server/ /app/server/
COPY --chown=uplifted:uplifted examples/ /app/examples/
COPY --chown=uplifted:uplifted docs/ /app/docs/
COPY --chown=uplifted:uplifted pyproject.toml /app/
COPY --chown=uplifted:uplifted README.md /app/

# Copy Docker utilities
COPY --chown=uplifted:uplifted docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=uplifted:uplifted docker/healthcheck.sh /usr/local/bin/healthcheck.sh

RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER uplifted

# Set working directory
WORKDIR $UPLIFTED_HOME

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Expose ports
EXPOSE 7541 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command
CMD ["server"]
