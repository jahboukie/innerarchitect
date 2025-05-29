# Performance Optimization Suite

A comprehensive suite of tools for optimizing the performance of the Inner Architect application.

## Features

- **Asset Optimization:** Minification, bundling, and caching of static assets
- **Database Query Caching:** Efficient caching of database queries
- **Memory Profiling:** Detection and prevention of memory leaks
- **Performance Monitoring:** Real-time monitoring and metrics collection
- **Image Optimization:** Lazy loading, responsive images, and format optimization
- **Code Splitting:** Dynamic loading of JavaScript modules
- **Response Compression:** Automatic compression of HTTP responses

## Installation

The Performance Optimization Suite is already included in the Inner Architect application. No additional installation is needed.

## Usage

### Basic Integration

To use the Performance Optimization Suite in your Flask application:

```python
from performance.integration import init_performance

# Initialize with Flask app
performance_suite = init_performance(app)
```

### Configuration

Configure the suite in your application's configuration file:

```python
# Enable/disable components
PERF_ASSET_OPTIMIZATION = True
PERF_QUERY_CACHE = True
PERF_MEMORY_PROFILING = True
PERF_MONITORING = True
PERF_RESPONSE_COMPRESSION = True
PERF_FRONTEND_OPTIMIZATION = True

# Component-specific settings
PERF_QUERY_CACHE_DEFAULT_EXPIRE = 300  # 5 minutes
PERF_MEMORY_MAX_SNAPSHOTS = 100
PERF_THRESHOLD_SLOW_REQUEST_MS = 500
```

### Decorators

Use the suite's decorators to optimize specific functions:

```python
from performance import optimize_query, profile_performance, profile_memory

# Cache database queries
@optimize_query(expire=300)
def get_user_data(user_id):
    return User.query.get(user_id)

# Profile performance
@profile_performance(name='data_processing')
def process_data(data):
    # Processing logic
    return result

# Profile memory usage
@profile_memory
def memory_intensive_task():
    # Memory-intensive operations
    return result
```

### Asset Optimization

To use the asset optimization in your templates:

```html
<!-- Use the asset_url filter -->
<link rel="stylesheet" href="{{ 'style.css'|asset_url }}">
<script src="{{ 'app.js'|asset_url }}"></script>
```

### Frontend Optimization

The suite includes JavaScript utilities for frontend optimization:

```html
<!-- Include the optimization scripts -->
{{ optimization_scripts|safe }}

<script>
// Load a feature module dynamically
CodeSplitter.loadFeature('chat', module => {
    module.init();
});

// Optimize images with lazy loading
ImageOptimizer.optimizeImages('img');

// Preload critical images
ImageOptimizer.preloadCriticalImages([
    '/static/images/hero.jpg',
    '/static/images/logo.png'
]);
</script>
```

## Command-Line Interface

The suite includes a command-line interface for optimization tasks:

```bash
# Optimize static assets
python optimize.py assets

# Clear caches
python optimize.py cache --clear

# Analyze memory usage
python optimize.py memory --leak-detection

# Profile an endpoint
python optimize.py profile /api/health -r 100
```

## Admin Dashboard

The suite provides an admin dashboard for monitoring performance:

```
/admin/performance/
```

The dashboard includes:
- Request performance metrics
- Memory usage charts
- Database query statistics
- System resource monitoring
- Optimization tools

## Components

### Asset Optimizer

```python
from performance import AssetOptimizer

# Initialize optimizer
optimizer = AssetOptimizer()

# Optimize all assets
manifest = optimizer.optimize_all()

# Get optimized asset URL
optimized_url = optimizer.get_asset_url('/static/js/app.js')
```

### Query Cache

```python
from performance import optimize_query, cache_query

# Option 1: Using the decorator
@optimize_query(expire=300)
def get_user_posts(user_id):
    return Post.query.filter_by(user_id=user_id).all()

# Option 2: Caching SQLAlchemy queries directly
def get_recent_users():
    query = User.query.order_by(User.created_at.desc()).limit(10)
    return query_cache.cache_query(query, key_prefix='recent_users')
```

### Memory Profiler

```python
from performance import MemoryProfiler, profile_memory

# Create profiler
profiler = MemoryProfiler()

# Take memory snapshot
snapshot = profiler.take_snapshot('explicit')

# Detect memory leaks
leak_info = profiler.detect_leaks()

# Profile a function
@profile_memory
def process_data():
    # Memory-intensive operation
    return result
```

### Performance Monitor

```python
from performance import PerformanceMonitor, profile_performance

# Create monitor
monitor = PerformanceMonitor()

# Profile a function
@profile_performance(name='api_request')
def handle_api_request():
    # Function implementation
    return response
```

## Example

See `performance_example.py` for a complete example of using the Performance Optimization Suite.

## Documentation

For more detailed information, see:
- [PERFORMANCE_OPTIMIZATION.md](../PERFORMANCE_OPTIMIZATION.md) - Comprehensive guide
- [PERFORMANCE_OPTIMIZATION_PLAN.md](../PERFORMANCE_OPTIMIZATION_PLAN.md) - Implementation plan

## License

This project is licensed under the same license as the Inner Architect application.