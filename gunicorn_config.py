"""Gunicorn configuration file"""
import os

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 60  # Increased timeout from default 30 seconds
keepalive = 2
max_requests = 0
max_requests_jitter = 0

# Server mechanics
daemon = False
preload_app = False
reload = False

# Logging
errorlog = '-'
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = None

# Server hooks
def on_starting(server):
    server.log.info("Starting server")

def on_exit(server):
    server.log.info("Stopping server")
