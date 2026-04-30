# Quantum RSS Radar - AI-assisted daily academic research tracking system
# Multi-stage Docker build for production

# Stage 1: Builder
FROM python:3.10-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 quantum && \
    mkdir -p /app && \
    chown quantum:quantum /app

# Switch to non-root user
USER quantum

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=quantum:quantum /root/.local /home/quantum/.local

# Add .local/bin to PATH
ENV PATH=/home/quantum/.local/bin:$PATH

# Copy application code
COPY --chown=quantum:quantum . .

# Create necessary directories
RUN mkdir -p data/raw data/all data/reports && \
    chown -R quantum:quantum data

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "src.orchestrator"]

# Expose port for web server (if running web interface)
EXPOSE 8000