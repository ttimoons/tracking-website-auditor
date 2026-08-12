FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=7070

WORKDIR /app

# Install basic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary and all Linux system dependencies
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Expose default app port (7070 for Flask)
EXPOSE 7070

# Default command: run Gunicorn for production
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
