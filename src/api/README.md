# Devmatrix REST API

Production-ready REST API for AI-powered workflow orchestration.

## Features

- **Workflow Management**: Full CRUD operations for workflow definitions
- **Execution Control**: Start, monitor, and cancel workflow executions
- **Observability**: Prometheus metrics, health checks, and structured logging
- **OpenAPI Documentation**: Interactive Swagger UI and ReDoc
- **Production Ready**: Error handling, CORS, validation, and monitoring

## Quick Start

### Installation

```bash
# Install dependencies
pip install fastapi uvicorn httpx

# Or using the project requirements
pip install -r requirements.txt
```

### Running the API

```bash
# Using uvicorn directly
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using the Python module
python -m src.api.main

# For production (without reload)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Accessing Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Root

- `GET /` - API information

### Workflows

- `POST /api/v1/workflows` - Create a new workflow
- `GET /api/v1/workflows` - List all workflows
- `GET /api/v1/workflows/{workflow_id}` - Get workflow by ID
- `PUT /api/v1/workflows/{workflow_id}` - Update workflow
- `DELETE /api/v1/workflows/{workflow_id}` - Delete workflow

### Executions

- `POST /api/v1/executions` - Start workflow execution
- `GET /api/v1/executions` - List all executions (with filters)
- `GET /api/v1/executions/{execution_id}` - Get execution status
- `POST /api/v1/executions/{execution_id}/cancel` - Cancel execution
- `DELETE /api/v1/executions/{execution_id}` - Delete execution

### Metrics

- `GET /api/v1/metrics` - Prometheus metrics export
- `GET /api/v1/metrics/summary` - Human-readable metrics summary

### Health

- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/live` - Kubernetes liveness probe
- `GET /api/v1/health/ready` - Kubernetes readiness probe

## Usage Examples

### Create a Workflow

```bash
curl -X POST "http://localhost:8000/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Processing Pipeline",
    "description": "Process and analyze data files",
    "tasks": [
      {
        "task_id": "fetch_data",
        "agent_type": "data_fetcher",
        "prompt": "Fetch data from source",
        "dependencies": [],
        "max_retries": 3,
        "timeout": 300
      },
      {
        "task_id": "process_data",
        "agent_type": "data_processor",
        "prompt": "Process and transform data",
        "dependencies": ["fetch_data"],
        "max_retries": 3,
        "timeout": 600
      }
    ]
  }'
```

### Start an Execution

```bash
curl -X POST "http://localhost:8000/api/v1/executions" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<workflow_id_from_previous_step>",
    "input_data": {
      "source_path": "/data/input",
      "output_path": "/data/output"
    },
    "priority": 5
  }'
```

### Monitor Execution Status

```bash
curl -X GET "http://localhost:8000/api/v1/executions/<execution_id>"
```

### Get Metrics

```bash
# Prometheus format
curl -X GET "http://localhost:8000/api/v1/metrics"

# Human-readable summary
curl -X GET "http://localhost:8000/api/v1/metrics/summary"
```

## Data Models

### Workflow

```json
{
  "name": "string",
  "description": "string (optional)",
  "tasks": [
    {
      "task_id": "string",
      "agent_type": "string",
      "prompt": "string",
      "dependencies": ["string"],
      "max_retries": 3,
      "timeout": 300
    }
  ],
  "metadata": {}
}
```

### Execution

```json
{
  "workflow_id": "string",
  "input_data": {},
  "priority": 5
}
```

## Configuration

### CORS

By default, CORS is configured to allow all origins. For production, update `src/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Environment Variables

- `API_HOST` - Host to bind (default: 0.0.0.0)
- `API_PORT` - Port to bind (default: 8000)
- `API_WORKERS` - Number of workers (default: 1)

## Testing

```bash
# Run API tests
python -m pytest tests/unit/api/ -v

# With coverage
python -m pytest tests/unit/api/ --cov=src/api --cov-report=html
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn

```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devmatrix-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devmatrix-api
  template:
    metadata:
      labels:
        app: devmatrix-api
    spec:
      containers:
      - name: api
        image: devmatrix-api:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Architecture

```
src/api/
├── __init__.py          # Module exports
├── app.py               # FastAPI application factory
├── main.py              # Entry point
├── examples.py          # API usage examples
├── README.md            # This file
└── routers/
    ├── workflows.py     # Workflow CRUD endpoints
    ├── executions.py    # Execution management endpoints
    ├── metrics.py       # Metrics and monitoring endpoints
    └── health.py        # Health check endpoints
```

## Monitoring

### Prometheus Integration

The API exposes metrics at `/api/v1/metrics` in Prometheus exposition format:

```
# TYPE workflows_total counter
workflows_total 15

# TYPE executions_total counter
executions_total 47

# TYPE executions_by_status_total counter
executions_by_status_total{status="completed"} 32
executions_by_status_total{status="running"} 3
executions_by_status_total{status="failed"} 8
```

### Health Checks

- `/api/v1/health` - Comprehensive component health
- `/api/v1/health/live` - Simple liveness check (returns 200 OK)
- `/api/v1/health/ready` - Readiness check (503 if not ready)

## Security Considerations

### Production Checklist

- [ ] Configure specific CORS origins
- [ ] Add authentication/authorization middleware
- [ ] Enable HTTPS/TLS
- [ ] Set up rate limiting
- [ ] Configure API keys or OAuth
- [ ] Enable request validation
- [ ] Set up logging and monitoring
- [ ] Use environment variables for secrets
- [ ] Implement request size limits
- [ ] Add security headers

## Performance

### Benchmarking

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/health

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/health
```

### Optimization Tips

1. **Use background tasks** for long-running operations
2. **Enable response caching** for read-heavy endpoints
3. **Add database connection pooling** when using real storage
4. **Use async/await** for I/O-bound operations
5. **Implement pagination** for list endpoints
6. **Add response compression** (gzip)

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Find process using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
```

**Import errors**
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**CORS errors**
- Check `allow_origins` in `src/api/app.py`
- Ensure preflight OPTIONS requests are handled

## Contributing

1. Add new endpoints in `src/api/routers/`
2. Update OpenAPI documentation with examples
3. Add tests in `tests/unit/api/`
4. Update this README

## License

See main project LICENSE file.
