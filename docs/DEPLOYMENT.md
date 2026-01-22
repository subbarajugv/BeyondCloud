# BeyondCloud Deployment Guide

Production deployment guide for the Python AI backend.

---

## Deployment Options

| Environment | Recommended Server | Scaling Approach |
|-------------|-------------------|------------------|
| **Kubernetes** | Uvicorn (direct) | Horizontal Pod Autoscaler |
| **VMs / Bare Metal** | Gunicorn + Uvicorn Workers | Process-based |
| **Docker Compose** | Either | Container replicas |
| **Development** | Uvicorn | Single process |

---

## Option 1: Kubernetes Deployment

For Kubernetes, use **uvicorn directly**. K8s handles scaling via replicas.

### Why Uvicorn for K8s?

- K8s provides health checks, restarts, and scaling
- Lighter memory footprint per pod
- Simpler debugging (one process per pod)
- HPA scales pods, not internal workers

### Startup Command

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1
```

### Kubernetes Deployment Config

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: beyondcloud-python
spec:
  replicas: 3  # K8s handles scaling
  template:
    spec:
      containers:
      - name: python-backend
        image: beyondcloud/python-backend:latest
        command: ["uvicorn"]
        args: ["main:app", "--host", "0.0.0.0", "--port", "8001"]
        ports:
        - containerPort: 8001
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: beyondcloud-python-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: beyondcloud-python
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Option 2: VM / Bare Metal Deployment

For VMs or bare metal, use **Gunicorn with Uvicorn workers**.

### Why Gunicorn for VMs?

- Process management and auto-restart
- Worker recycling prevents memory leaks
- Graceful reloads (zero-downtime deploys)
- Battle-tested (10+ years in production)

### Quick Start

```bash
cd backend-python
pip install -r requirements.txt

# Production mode
gunicorn -c gunicorn.conf.py main:app
```

### Configuration

The `gunicorn.conf.py` file provides sensible defaults. Override via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GUNICORN_BIND` | `0.0.0.0:8001` | Host:port to bind |
| `GUNICORN_WORKERS` | `(CPU * 2) + 1` | Number of worker processes |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout (seconds) |
| `GUNICORN_MAX_REQUESTS` | `1000` | Requests before worker restart |
| `GUNICORN_LOG_LEVEL` | `info` | Logging verbosity |

### Example: 4-Core Server

```bash
export GUNICORN_WORKERS=9      # 4 * 2 + 1
export GUNICORN_TIMEOUT=180    # Longer for embedding ops
gunicorn -c gunicorn.conf.py main:app
```

### Systemd Service (Recommended)

Create `/etc/systemd/system/beyondcloud-python.service`:

```ini
[Unit]
Description=BeyondCloud Python Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=beyondcloud
Group=beyondcloud
WorkingDirectory=/opt/beyondcloud/backend-python
Environment="PATH=/opt/beyondcloud/venv/bin"
Environment="GUNICORN_WORKERS=9"
ExecStart=/opt/beyondcloud/venv/bin/gunicorn -c gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable beyondcloud-python
sudo systemctl start beyondcloud-python
```

### Zero-Downtime Reload

```bash
sudo systemctl reload beyondcloud-python
# Gunicorn gracefully restarts workers
```

---

## Option 3: Docker Compose

For development or small deployments:

```yaml
version: '3.8'
services:
  python-backend:
    build: ./backend-python
    command: >
      gunicorn -c gunicorn.conf.py main:app
    environment:
      - DATABASE_URL=postgresql://...
      - GUNICORN_WORKERS=4
    ports:
      - "8001:8001"
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Reverse Proxy Configuration

### Nginx (Recommended)

```nginx
upstream beyondcloud_python {
    least_conn;
    server 127.0.0.1:8001;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.beyondcloud.example.com;

    ssl_certificate /etc/ssl/certs/beyondcloud.crt;
    ssl_certificate_key /etc/ssl/private/beyondcloud.key;

    location / {
        proxy_pass http://beyondcloud_python;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # Streaming support for SSE
        proxy_buffering off;
        proxy_cache off;
        
        # Timeouts for long-running operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Health check bypass (no auth needed)
    location /health {
        proxy_pass http://beyondcloud_python;
        access_log off;
    }
}
```

---

## Health Checks

The backend provides three health endpoints:

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `/health/live` | Liveness | App is running |
| `/health/ready` | Readiness | DB connected, services up |
| `/health/deep` | Deep health | All dependencies + latency |

### Monitoring Integration

```bash
# Prometheus scrape target
curl -s http://localhost:8001/health/deep | jq .
```

---

## Performance Tuning

### Worker Count Formula

| Workload | Formula | Example (8-core) |
|----------|---------|------------------|
| I/O-bound (API calls) | `(CPU * 2) + 1` | 17 workers |
| CPU-bound (embeddings) | `CPU + 1` | 9 workers |
| Mixed | `CPU * 1.5` | 12 workers |

### Memory Considerations

| Worker Count | RAM per Worker | Total RAM |
|--------------|----------------|-----------|
| 9 workers | ~200MB (light) | ~2GB |
| 9 workers | ~500MB (with models) | ~5GB |

### Worker Recycling

Prevent memory leaks with periodic restarts:

```bash
export GUNICORN_MAX_REQUESTS=1000
export GUNICORN_MAX_REQUESTS_JITTER=50
```

---

## Troubleshooting

### Workers Timing Out

```bash
# Increase timeout for long embedding operations
export GUNICORN_TIMEOUT=300
```

### Memory Growing Unbounded

```bash
# Enable worker recycling
export GUNICORN_MAX_REQUESTS=500
```

### Connection Refused

```bash
# Check if service is running
systemctl status beyondcloud-python

# Check logs
journalctl -u beyondcloud-python -f
```

### Graceful Shutdown Issues

```bash
# Increase graceful timeout
# Edit gunicorn.conf.py: graceful_timeout = 60
```

---

## Security Checklist

- [ ] Run as non-root user
- [ ] Use reverse proxy for SSL termination
- [ ] Enable firewall (only expose via proxy)
- [ ] Set `GUNICORN_BIND=127.0.0.1:8001` if behind proxy
- [ ] Rotate logs with logrotate
- [ ] Monitor with Prometheus/Grafana
