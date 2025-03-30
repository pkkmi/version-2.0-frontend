import os
import multiprocessing

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "8080")
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 60  # Increased timeout to handle slower MongoDB connections
keepalive = 2

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = '-'
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = None

# Server hooks
def on_starting(server):
    """Log that Gunicorn is starting the Andikar AI frontend."""
    server.log.info("Starting Andikar AI Web Frontend")

def on_exit(server):
    """Log that Gunicorn is shutting down."""
    server.log.info("Shutting down Andikar AI Web Frontend")

def post_fork(server, worker):
    """Set up worker after fork."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    """Prepare to fork a worker."""
    pass

def pre_exec(server):
    """Just before we exec a new process."""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called when the server is ready to accept connections."""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called when a worker gets SIGINT or SIGTERM."""
    worker.log.info(f"Worker received SIGINT or SIGTERM (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info(f"Worker was aborted (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info(f"Worker exited (pid: {worker.pid})")
