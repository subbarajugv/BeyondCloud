"""
Gunicorn configuration for production VM deployments.

Usage:
    gunicorn -c gunicorn.conf.py main:app

For Kubernetes, use uvicorn directly (K8s handles scaling):
    uvicorn main:app --host 0.0.0.0 --port 8001
"""
import multiprocessing
import os

# =============================================================================
# Server Socket
# =============================================================================

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8001")
backlog = 2048

# =============================================================================
# Worker Processes
# =============================================================================

# Use Uvicorn workers for async support
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers: 2-4 x CPU cores for I/O bound apps
# For CPU-bound (embeddings), use 1-2 x CPU cores
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Threads per worker (for sync workers only, not used with UvicornWorker)
threads = 1

# =============================================================================
# Worker Lifecycle
# =============================================================================

# Restart workers after this many requests (prevents memory leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 50))

# Graceful timeout for worker shutdown
graceful_timeout = 30

# Worker timeout (kill unresponsive workers)
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))

# Time to wait for requests on Keep-Alive connections
keepalive = 5

# =============================================================================
# Server Mechanics
# =============================================================================

# Daemonize the Gunicorn process (set to True for systemd)
daemon = False

# PID file location
pidfile = os.getenv("GUNICORN_PIDFILE", None)

# User/Group to run as (for privilege dropping)
user = os.getenv("GUNICORN_USER", None)
group = os.getenv("GUNICORN_GROUP", None)

# Working directory
chdir = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# Logging
# =============================================================================

# Access log
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" = stdout
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# Error log
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # "-" = stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Capture stdout/stderr from workers
capture_output = True

# =============================================================================
# Security
# =============================================================================

# Limit request line size (URL + headers)
limit_request_line = 4094

# Limit request header fields
limit_request_fields = 100

# Limit request header field size
limit_request_field_size = 8190

# =============================================================================
# SSL (Optional - usually handled by reverse proxy)
# =============================================================================

# Uncomment for direct SSL termination:
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
# ssl_version = "TLSv1_2"
# ciphers = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"

# =============================================================================
# Hooks
# =============================================================================

def on_starting(server):
    """Called before the master process is initialized."""
    print("🚀 BeyondCloud Python Backend starting...")
    print(f"   Workers: {workers}")
    print(f"   Bind: {bind}")
    print(f"   Worker class: {worker_class}")


def on_reload(server):
    """Called before reloading workers."""
    print("🔄 Reloading workers...")


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"⚠️  Worker {worker.pid} interrupted")


def worker_abort(worker):
    """Called when a worker receives SIGABRT (timeout)."""
    print(f"❌ Worker {worker.pid} aborted (timeout)")


def child_exit(server, worker):
    """Called when a worker process exits."""
    print(f"👋 Worker {worker.pid} exited")


def post_fork(server, worker):
    """Called after a worker has been forked."""
    print(f"✅ Worker {worker.pid} spawned")
