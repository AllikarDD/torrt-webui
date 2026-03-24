# Alternative: Build your web app as a standalone executable
FROM python:3.11-slim as builder

RUN pip install --no-cache-dir pyinstaller

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ ./templates/

# Build executable
RUN pyinstaller --onefile --name torrt-webui app.py

# Final stage
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install torrt
RUN git clone https://github.com/idlesign/torrt.git /tmp/torrt && \
    cd /tmp/torrt && \
    pip install --no-cache-dir . && \
    rm -rf /tmp/torrt

# Copy executable from builder
COPY --from=builder /build/dist/torrt-webui /usr/local/bin/

# Create config directory
RUN mkdir -p /root/.config/torrt /var/log/torrt

COPY config/torrt_config.py /root/.config/torrt/config.py.default

EXPOSE 5000

CMD ["torrt-webui"]