FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Copy entrypoint script for APP_PORT configuration
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Envoy sidecar exposes 9000, app listens on APP_PORT)
EXPOSE 9001

# Entrypoint sets APP_PORT environment variable (default: 9001)
# Override by setting APP_PORT in docker-compose.yml environment section
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run application using $APP_PORT from entrypoint
# Envoy sidecar handles mTLS and exposes service on port 9000
CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port $APP_PORT"]
