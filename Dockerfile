# Multi-stage Dockerfile for Claude Code Chatbot

# Backend stage
FROM python:3.11-slim as backend

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Frontend stage
FROM python:3.11-slim as frontend

WORKDIR /app/frontend

# Copy frontend requirements and install
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code
COPY frontend/ .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY --from=backend /app/backend /app/backend
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy frontend
COPY --from=frontend /app/frontend /app/frontend

# Install dependencies again to ensure everything is available
COPY backend/requirements.txt /app/backend/
COPY frontend/requirements.txt /app/frontend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt -r /app/frontend/requirements.txt

# Create workspaces directory
RUN mkdir -p /app/workspaces

# Expose ports
EXPOSE 8000 8501

# Copy startup script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
