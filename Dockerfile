# OPC200 Docker Image
# One Person Company AI Support Platform

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements-test.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY skills/ ./skills/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY pyproject.toml ./
COPY README.md ./

# Install the package
RUN pip install --no-cache-dir -e .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/backups

# Non-root user for security
RUN useradd -m -u 1000 opc200 && \
    chown -R opc200:opc200 /app
USER opc200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import opc200; print('OK')" || exit 1

# Expose port (if needed for API)
EXPOSE 8000

# Default command
CMD ["python", "-m", "opc200"]
