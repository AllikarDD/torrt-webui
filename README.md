# torrt Web UI

A web interface for torrt - torrent automation tool.

## Features

- Manage RPC clients (Transmission, qBittorrent, Deluge, uTorrent)
- Configure trackers with credentials
- Add, remove, register, and unregister torrents
- Run torrent updates
- View all registered torrents

## Quick Start

### Using Docker

```bash
docker run -d \
  --name torrt-webui \
  -p 5000:5000 \
  -v $(pwd)/torrt-config:/root/.torrt \
  yourusername/torrt-webui:latest
```

### Using Docker-Compose

```bash
version: '3.8'

services:
  torrt-webui:
    image: yourusername/torrt-webui:latest
    container_name: torrt-webui
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - TORRT_PATH=/usr/local/bin/torrt
      - PORT=5000
    volumes:
      - ./torrt-config:/root/.torrt
```