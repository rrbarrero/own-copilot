# Use a Debian-based Python image with uv pre-installed (better wheel support)
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder

# Set the working directory
WORKDIR /app

# Install system dependencies including Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock ./

# Install ALL dependencies (including dev)
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . .

# Install the project
RUN uv sync --frozen


# Final image (we use uv for the final image to have access to dev tools)
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

# Install runtime dependencies including Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the environment from the builder
COPY --from=builder /app /app

# Set environments
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
