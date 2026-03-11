# ---------- Frontend build stage ----------
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/crypto-risk-dashboard

COPY crypto-risk-dashboard/package.json ./
COPY crypto-risk-dashboard/package-lock.json ./

RUN npm ci

COPY crypto-risk-dashboard/ ./
RUN npm run build


# ---------- Backend runtime stage ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY core ./core
COPY data ./data
COPY artifacts ./artifacts

COPY --from=frontend-builder /app/crypto-risk-dashboard/dist ./crypto-risk-dashboard/dist

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
