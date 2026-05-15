FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install torrt and web app dependencies
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torrt

# Create torrents config directory
RUN mkdir -p /root/.torrt

# Copy application files
COPY templates/ ./templates/
COPY static/ ./static/
COPY src/ ./src/

# Expose app port and run
EXPOSE 5000
CMD ["python", "src/app.py"]

