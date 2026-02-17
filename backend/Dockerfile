# Use official Playwright Python image (includes browser binaries + deps)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install bash (required for start.sh)
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

# Create storage directories
RUN mkdir -p /app/storage/guidelines /app/storage/exports

# Make start script executable
RUN chmod +x /app/scripts/start.sh

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
