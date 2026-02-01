FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ src/

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "h3_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
