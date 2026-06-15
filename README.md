
# torrt Web UI

A web interface for torrt - torrent automation tool.

## Features

- Manage RPC clients (Transmission, qBittorrent, Deluge, uTorrent)
- Configure trackers with credentials
- Add, remove, register, and unregister torrents
- Run torrent updates
- View all registered torrents

## Docker Commands

### Build the Docker Image

```bash
# Build with default tag
docker build -t torrt-webui .

# Build with specific tag
docker build -t torrt-webui:latest .

# Build with custom username/repo
docker build -t yourusername/torrt-webui:latest .
```

### Run the Container

```bash
# Basic run
docker run -d \
  --name torrt-webui \
  -p 5000:5000 \
  -v $(pwd)/torrt-config:/root/.torrt \
  torrt-webui:latest

# Run with custom port mapping
docker run -d \
  --name torrt-webui \
  -p 8080:5000 \
  -v $(pwd)/torrt-config:/root/.torrt \
  torrt-webui:latest

# Run with environment variables
docker run -d \
  --name torrt-webui \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e PORT=5000 \
  -v $(pwd)/torrt-config:/root/.torrt \
  torrt-webui:latest
```

### Execute Commands in Container

```bash
# Open bash shell in running container
docker exec -it torrt-webui /bin/bash

# Run torrt commands
docker exec -it torrt-webui torrt --help
docker exec -it torrt-webui torrt clients list
docker exec -it torrt-webui torrt trackers list

# Check logs
docker exec -it torrt-webui cat /var/log/torrt-webui.log

# List directory contents
docker exec -it torrt-webui ls -la /root/.torrt

# Check running processes
docker exec -it torrt-webui ps aux

# Test web service internally
docker exec -it torrt-webui curl http://localhost:5000

# Run Python commands
docker exec -it torrt-webui python -c "import torrt; print(torrt.__version__)"
```

### Container Management Commands

```bash
# Stop container
docker stop torrt-webui

# Start container
docker start torrt-webui

# Restart container
docker restart torrt-webui

# Remove container
docker rm -f torrt-webui

# View container logs
docker logs torrt-webui
docker logs -f torrt-webui  # Follow logs

# Inspect container
docker inspect torrt-webui

# View resource usage
docker stats torrt-webui
```

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

Create a `docker-compose.yml` file:

```yaml
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

Run with Docker-Compose:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Execute commands
docker-compose exec torrt-webui torrt clients list
```

### Build and Run Workflow Example

```bash
# 1. Build the image
docker build -t torrt-webui:latest .

# 2. Run the container
docker run -d --name torrt-webui -p 5000:5000 torrt-webui:latest

# 3. Check if it's running
docker ps | grep torrt-webui

# 4. View logs
docker logs torrt-webui

# 5. Execute commands inside
docker exec -it torrt-webui torrt clients list

# 6. Stop and remove when done
docker stop torrt-webui && docker rm torrt-webui
```



```
docker stop torrt-webui; docker rm torrt-webui; docker build -t torrt-webui .; docker run -d --name torrt-webui -p 5000:5000 torrt-webui; docker exec -it torrt-webui bash



 cat /var/log/torrtwebui/log.txt 
```
docker build -t torrt-webui:1.0.5 .
docker build -t torrt-webui:latest .

docker push allikardd/torrt-webui:1.0.5
docker push allikardd/torrt-webui:latest


Build and Publish to Docker Hub
Login to Docker Hub:

```bash
docker login
```
# Build the image:
Build with your Docker Hub username

```bash

```
# Push to Docker Hub:

Push all tags

```bash
docker build -t allikardd/torrt-webui:latest .
docker build -t allikardd/torrt-webui:1.1.0 .
docker push allikardd/torrt-webui:latest
docker push allikardd/torrt-webui:1.1.0
```