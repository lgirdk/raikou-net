# Stage 1 — build the React SPA.
# Output: /app/frontend/dist/ with index.html + hashed JS/CSS bundles.
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit

COPY frontend/ .
# Vite writes the production build to dist/ by default.
RUN npm run build

# Stage 2 — run the FastAPI backend.
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install Python deps (no requirements.txt — install inline, pinned loosely).
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" httpx

COPY backend/ ./backend/

# Copy the built SPA into the location main.py expects.
COPY --from=frontend-build /app/frontend/dist/ ./backend/static/

ENV ORCHESTRATOR_URL=http://host.docker.internal:8080

EXPOSE 9090

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9090"]
