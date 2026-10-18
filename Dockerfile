# Use official lightweight Python image
FROM python:3.11-slim

# Prevent writing .pyc files and enable live log output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for compiling psycopg and handling SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose internal Streamlit port
EXPOSE 8501

# Health check to ensure the dashboard container is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch main Streamlit entry point
CMD ["streamlit", "run", "1_📊_Load_Booking.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]