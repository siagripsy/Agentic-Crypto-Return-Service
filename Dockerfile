# ---------- Frontend build stage ----------
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/crypto-risk-dashboard

COPY crypto-risk-dashboard/package.json ./
COPY crypto-risk-dashboard/package-lock.json ./
RUN npm ci --include=optional
RUN node -e "require('rollup'); require('@rollup/rollup-linux-x64-gnu')"

COPY crypto-risk-dashboard/ ./
RUN npm run build


# ---------- Backend runtime stage ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    ACCEPT_EULA=Y

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    libgomp1 \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && echo "[ODBC Driver 18 for SQL Server]" >> /etc/odbcinst.ini \
    && echo "Description=Microsoft ODBC Driver 18 for SQL Server" >> /etc/odbcinst.ini \
    && echo "Driver=/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.so" >> /etc/odbcinst.ini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY core ./core
COPY artifacts ./artifacts

COPY --from=frontend-builder /app/crypto-risk-dashboard/dist ./crypto-risk-dashboard/dist

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
