FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create static directory if it doesn't exist
RUN mkdir -p static

# Expose port
EXPOSE 5505

# Set environment variables
ENV FLASK_ENV=production
ENV PORT=5505

# Run with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5505", "--workers", "2", "--threads", "2", "--timeout", "120"]
