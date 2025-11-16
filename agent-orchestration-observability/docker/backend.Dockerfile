FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend files
COPY backend/ ./backend/
COPY pyproject.toml .

# Install dependencies
RUN uv sync

# Expose backend port
EXPOSE 8765

# Run the backend
CMD ["uv", "run", "backend/main.py"]
