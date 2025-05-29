import os
import multiprocessing

# Bind to 0.0.0.0:5000
bind = "0.0.0.0:5000"

# Number of worker processes
# If WEB_CONCURRENCY environment variable is set, use that
# Otherwise, use (2 * number of cores) + 1, which is a common formula
workers = int(os.environ.get("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))

# Use a basic worker (sync)
worker_class = "sync"

# Timeout for workers (in seconds)
timeout = 120

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50  # Adds randomness to max_requests

# Preload the application
preload_app = True

# Log level
loglevel = "info"

# Access log format
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr

# Capture log output from the application itself
capture_output = True