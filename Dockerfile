# syntax=docker/dockerfile:1

### Build stage ###
FROM python:3.13-alpine AS build

# Install build dependencies for Pillow and other native wheels
RUN apk add --no-cache \
    build-base \
    jpeg-dev zlib-dev freetype-dev

# Copy uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Copy only app source files
COPY blueprints blueprints
COPY main.py server.py curl.py tools.py mail.py cache_helper.py ./
COPY templates templates
COPY data data
COPY pwa pwa
COPY .well-known .well-known

# Clean up caches and pycache
RUN rm -rf /root/.cache/uv
RUN find . -type d -name "__pycache__" -exec rm -rf {} +


### Runtime stage ###
FROM python:3.13-alpine AS runtime
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup -h /app appuser

WORKDIR /app
RUN apk add --no-cache curl


# Copy only whats needed for runtime
COPY --from=build --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=build --chown=appuser:appgroup /app/templates /app/templates
COPY --from=build --chown=appuser:appgroup /app/main.py /app/
COPY --from=build --chown=appuser:appgroup /app/server.py /app/

USER appuser
EXPOSE 5000

ENTRYPOINT ["python3", "main.py"]
