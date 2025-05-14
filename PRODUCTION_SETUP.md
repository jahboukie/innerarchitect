# Production Setup Guide

This guide provides instructions for configuring The Inner Architect for production deployment.

## Step 1: Apply Production Configuration

To use the production configuration, add the following code to `main.py`:

```python
if __name__ == "__main__":
    # Development mode
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # Production mode (when running under Gunicorn)
    from production_config import apply_production_config
    app = apply_production_config(app)
```

## Step 2: Configure Gunicorn

Create a `gunicorn_config.py` file with the following content:

```python
# Gunicorn configuration for production
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 4
timeout = 120
keepalive = 65

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = "-"
loglevel = "info"
accesslog = "-"
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "inner_architect"

# Server hooks
def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")

def worker_exit(server, worker):
    server.log.info("Worker exited (pid: %s)", worker.pid)
```

## Step 3: Update .replit File

Update the `.replit` file to use Gunicorn in production:

```
run = "gunicorn -c gunicorn_config.py main:app"
```

## Step 4: Monitoring Setup

Integrate the monitoring configuration by adding this to `app.py`:

```python
# Set up monitoring in production
if not app.debug:
    from monitoring_config import setup_monitoring_endpoints
    setup_monitoring_endpoints(app)
```

## Step 5: Configure Health Checks

Set up a simple health check endpoint that Replit can use to verify the application is running:

```python
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})
```

## Step 6: Database Connection Pooling

Ensure database connection pooling is properly configured in `app.py`:

```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 10,
    "max_overflow": 20
}
```

## Step 7: Error Pages

Create custom error pages for production:

1. Create templates for error pages:
   - `templates/errors/404.html`
   - `templates/errors/500.html`

2. Register error handlers in `app.py`:

```python
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500
```

## Step 8: Static Assets Optimization

Optimize static assets for production:

1. Add cache headers for static assets:

```python
@app.after_request
def add_cache_headers(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        # Do not cache HTML
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    elif request.path.startswith('/static/'):
        # Cache static assets for 1 week
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response
```

## Step 9: Security Headers

Add security headers to all responses:

```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

## Step 10: Verify Production Readiness

Before deploying, run through this checklist:

- [ ] Debug mode is disabled
- [ ] All sensitive API keys are stored as environment variables
- [ ] Database connection pooling is configured
- [ ] Static assets are properly cached
- [ ] Error pages are configured
- [ ] Security headers are in place
- [ ] Health check endpoint is working
- [ ] Monitoring endpoints are configured
- [ ] Gunicorn is configured correctly

## Deployment

Once you've completed the production setup, deploy using the Replit deployment tools:

1. Click on the "Deploy" button in the Replit interface
2. Fill in the deployment details (name, description, etc.)
3. Review the deployment settings
4. Start the deployment

After deployment, verify that the application is working correctly by:

1. Testing the health check endpoint
2. Checking that authentication is working
3. Verifying subscription management
4. Testing AI conversation functionality
5. Checking the monitoring endpoints