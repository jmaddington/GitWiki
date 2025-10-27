FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    postgresql-client \
    libpq-dev \
    redis-tools \
    curl \
    vim \
    nano \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 -m vscode \
    && mkdir -p /home/vscode/.vscode-server /home/vscode/.vscode-server-insiders \
    && chown -R vscode:vscode /home/vscode

# Create app directory
RUN mkdir -p /workspace /app/wiki-repo \
    && chown -R vscode:vscode /workspace /app

# Set working directory
WORKDIR /workspace

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Create logs directory
RUN mkdir -p /workspace/logs \
    && chown -R vscode:vscode /workspace/logs

# Switch to non-root user
USER vscode

# Expose Django development server port
EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
