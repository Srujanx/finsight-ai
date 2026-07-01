# Stage 1: build the React frontend.
FROM node:20-slim AS frontend
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Python backend that serves the built frontend.
FROM python:3.12-slim
WORKDIR /app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install Python deps.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy app code and the built frontend from stage 1.
COPY README.md ./
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY --from=frontend /web/dist ./web/dist

# HF Spaces expects the app on port 7860.
ENV PORT=7860
EXPOSE 7860
CMD ["uv", "run", "uvicorn", "finsight.api:app", "--host", "0.0.0.0", "--port", "7860"]
