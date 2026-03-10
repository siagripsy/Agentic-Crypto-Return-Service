# ---------- Frontend build stage ----------
# ---------- Frontend build ----------
FROM node:20 AS frontend-builder

WORKDIR /app/crypto-risk-dashboard

COPY crypto-risk-dashboard/package.json ./
COPY crypto-risk-dashboard/package-lock.json ./

# Work around npm optional-dependency issue for Rollup on Linux
RUN rm -f package-lock.json && npm install

COPY crypto-risk-dashboard/ ./
RUN npm run build


# ---------- Backend runtime stage ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pandas \
    numpy \
    scikit-learn \
    fastapi \
    uvicorn \
    pydantic \
    requests \
    yfinance \
    python-dotenv \
    httpx \
    joblib \
    streamlit \
    matplotlib \
    google-genai

# Copy backend code
COPY app ./app
COPY core ./core
COPY data ./data
COPY artifacts ./artifacts

# Copy built frontend
COPY --from=frontend-builder /app/crypto-risk-dashboard/dist ./crypto-risk-dashboard/dist

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]