# ── Stage 1: build the React SPA ────────────────────────
FROM node:20-slim AS build-frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# The API base is baked into the bundle at build time.
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN npm run build

# ── Stage 2: python runtime ─────────────────────────────
FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY --from=build-frontend /app/dist ./dist
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi", "--chdir", "./src/"]
