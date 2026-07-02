"""Gunicorn configuration.

Gunicorn auto-loads this file from the working directory (/app in the container).
Command-line flags in backend.entrypoint.sh still take precedence over the values
set here.

Threaded workers keep a single half-open or slow connection (e.g. a browser
preconnect or a bare TCP health check that never sends an HTTP request) from
blocking the whole server, which is what caused the "WORKER TIMEOUT (no URI read)"
crashes with the default single sync worker.
"""

bind = "0.0.0.0:8000"

# A few worker processes, each with several threads. One stalled connection now
# only ties up one thread instead of the entire server.
workers = 2
worker_class = "gthread"
threads = 4

# Give slow clients more room than the 30s default before the arbiter aborts a
# worker.
timeout = 60
graceful_timeout = 30

# Recycle idle keep-alive connections reasonably quickly.
keepalive = 5
