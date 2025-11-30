FROM python:3.11-slim

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8766

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

# Run the server
CMD ["python", "-m", "src.main"]
