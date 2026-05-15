FROM python:3.13-slim

# Install torrt and web app dependencies
RUN pip install --no-cache-dir torrt flask flask-wtf

# Create directories
RUN mkdir -p /root/.torrt /app

WORKDIR /app

# Copy web app
COPY templates/ ./templates/
COPY src/ ./src/
COPY static/ ./static/

# Create entrypoint
RUN echo '#!/bin/bash\n\
exec python src/app.py\n' > /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]