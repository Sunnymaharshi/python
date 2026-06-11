# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Use the official uv image — comes with uv pre-installed, no manual install needed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable uv bytecode compilation and frozen installs for reproducible builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy

# Copy dependency files first — Docker caches this layer
# Only re-runs if pyproject.toml or uv.lock changes (not on every code change)
COPY pyproject.toml uv.lock* README.md ./

# Install only production deps — no dev tools (pytest, locust, ruff) in the image
RUN uv sync --no-dev --no-install-project

# Now copy source code and install the package itself
COPY src/ ./src/
RUN uv sync --no-dev


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Lean final image — no uv, no build tools, just Python + our app
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Create a non-root user — never run production apps as root
RUN groupadd --system app && useradd --system --gid app app

# Copy the fully built venv from builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src   /app/src

# Put the venv on PATH so Python finds our installed packages
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

# Health check — Docker marks container unhealthy if /health stops responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.rate_limiter.main:app", "--host", "0.0.0.0", "--port", "8000"]