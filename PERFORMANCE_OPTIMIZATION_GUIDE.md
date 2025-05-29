# Performance Optimization Suite

The Performance Optimization Suite is a comprehensive collection of tools and utilities designed to enhance the performance of the Inner Architect application. It provides features for optimizing assets, caching database queries, monitoring memory usage, and improving overall application responsiveness.

## Features

### 1. Caching System
- **Multi-backend support**: Memory, Redis, and Memcached cache backends
- **Query caching**: Automatically cache database query results
- **Decorator-based API**: Simple `@optimize_query` decorator for caching functions
- **Cache invalidation**: Intelligent cache invalidation strategies

### 2. Content Delivery Optimization
- **Asset optimization**: Minification and bundling of CSS and JavaScript
- **Content hashing**: Automatic cache busting for static assets
- **Image optimization**: Compression and optimization of image assets
- **CDN integration**: Support for content delivery networks

### 3. Database Optimization
- **Query performance tracking**: Identify slow queries automatically
- **Connection pooling**: Efficient database connection management
- **Query optimization**: Automatic query optimization suggestions
- **Query result caching**: Cache frequently used query results

### 4. Response Optimization
- **HTTP compression**: Automatic gzip compression of responses
- **ETag support**: Conditional requests to reduce bandwidth
- **Cache-Control management**: Proper HTTP caching headers
- **Conditional responses**: 304 Not Modified responses when appropriate

### 5. Performance Monitoring
- **Request timing**: Track and analyze request durations
- **Memory profiling**: Monitor application memory usage
- **System resource tracking**: CPU, memory, and disk usage metrics
- **Performance dashboard**: Visual representation of performance data

## Integration

The Performance Optimization Suite is designed to be easily integrated with the main Inner Architect application. The integration is handled through the `app_performance.py` module, which provides a simple entry point for setting up all performance components.

```python
from app_performance import integrate_performance_optimization

# Initialize Flask app
app = Flask(__name__)

# Integrate performance optimization
integrate_performance_optimization(app)
```

## Configuration

The Performance Optimization Suite can be configured through the Flask application's configuration. Below are the available configuration options:

```python
# General settings
app.config['PERF_ENABLED'] = True
app.config['PERF_ADMIN_UI'] = True

# Component settings
app.config['PERF_ASSET_OPTIMIZATION'] = True
app.config['PERF_QUERY_CACHE'] = True
app.config['PERF_MEMORY_PROFILING'] = True
app.config['PERF_MONITORING'] = True
app.config['PERF_RESPONSE_COMPRESSION'] = True
app.config['PERF_FRONTEND_OPTIMIZATION'] = True

# Cache settings
app.config['PERF_CACHE_TYPE'] = 'memory'  # 'memory', 'redis', or 'memcached'
app.config['PERF_CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes

# Performance thresholds
app.config['PERF_SLOW_REQUEST_THRESHOLD'] = 0.5  # seconds
app.config['PERF_SLOW_QUERY_THRESHOLD'] = 0.1  # seconds
app.config['PERF_HIGH_MEMORY_THRESHOLD'] = 200  # MB

# Optimization settings
app.config['PERF_OPTIMIZE_ASSETS_ON_STARTUP'] = not app.debug
app.config['PERF_MINIFY_HTML'] = not app.debug
app.config['PERF_ADD_TIMING_HEADERS'] = True

# Monitoring settings
app.config['PERF_MONITOR_SYSTEM_RESOURCES'] = True
app.config['PERF_API_ENDPOINTS'] = True
```

## Usage

### Caching Database Queries

```python
from performance.performance_suite import optimize_query

@optimize_query(expire=300)
def get_user_data(user_id):
    # Database query here
    return result
```

### Performance Profiling

```python
from performance.performance_suite import profile_performance

@profile_performance()
def process_data():
    # Data processing here
    return result
```

### Memory Profiling

```python
from performance.performance_suite import profile_memory

@profile_memory
def memory_intensive_function():
    # Memory-intensive operations here
    return result
```

### Asset Optimization

```html
<!-- In templates, use the asset_url filter -->
<link rel="stylesheet" href="{{ 'static/style.css'|asset_url }}">
<script src="{{ 'static/script.js'|asset_url }}"></script>
```

## Administration

The Performance Optimization Suite includes an admin dashboard for monitoring and managing performance. The dashboard is available at `/admin/performance` and provides information on:

- Request performance
- Memory usage
- Database queries
- System resources

The dashboard also provides tools for:
- Optimizing assets
- Clearing caches
- Viewing performance metrics

## Dependencies

The Performance Optimization Suite has the following dependencies:

- **Required**:
  - Flask (core dependency)
  
- **Optional**:
  - Redis (for Redis cache backend)
  - pymemcache (for Memcached cache backend)
  - psutil (for system resource monitoring)
  - cssmin (for CSS minification)
  - jsmin (for JavaScript minification)
  - pillow (for image optimization)

## Installation

The Performance Optimization Suite is included with the Inner Architect application and does not require separate installation. However, to enable all features, you should install the optional dependencies:

```bash
pip install redis pymemcache psutil cssmin jsmin pillow
```

## CLI Commands

The Performance Optimization Suite adds the following CLI commands to the Flask application:

```bash
# Run asset optimization
flask perf optimize

# Clear all caches
flask perf clear-caches
```

## API Endpoints

The Performance Optimization Suite exposes the following API endpoints:

- `/api/performance/status`: Get the status of the performance suite
- `/api/performance/requests`: Get request performance data
- `/api/performance/memory`: Get memory usage data
- `/api/performance/queries`: Get query performance data
- `/api/performance/system`: Get system resource data
- `/api/performance/client`: Submit client-side performance metrics