# Phase 4: User Guide - Using DevMatrix Generated Applications

**Status**: ✅ **COMPLETE**
**Updated**: 2025-11-23
**Target**: End users of DevMatrix-generated applications

---

## 1. Getting Started with Generated Applications

### 1.1 What You Get

When DevMatrix generates an application, you receive:

```
your-app/
├── src/
│   ├── models/           # Database models (SQLAlchemy ORM)
│   ├── schemas/          # API request/response validation (Pydantic)
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic layer
│   ├── api/routes/       # FastAPI route handlers
│   ├── core/             # Configuration, database, security
│   └── main.py           # Application entry point
│
├── tests/                # Comprehensive test suite
├── docker/               # Docker configuration
├── migrations/           # Database schema migrations
├── Dockerfile            # Container definition
├── docker-compose.yml    # Local development environment
├── pyproject.toml        # Python dependencies (Poetry)
├── .env.example          # Environment variables template
├── README.md             # Quick start guide
├── openapi.json          # API specification
└── requirements.txt      # Pip requirements (alternative)
```

### 1.2 Quick Start (5 minutes)

**1. Extract and navigate:**
```bash
unzip your-app.zip
cd your-app
```

**2. Set up environment:**
```bash
cp .env.example .env
# Edit .env with your configuration (database, ports, etc.)
```

**3. Start development server:**
```bash
# Option A: Using Docker (recommended)
docker-compose up -d

# Option B: Local Python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

**4. Access the application:**
- **API Base URL**: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## 2. API Usage

### 2.1 Interactive Documentation

The easiest way to use the API is through Swagger UI:

1. Go to `http://localhost:8000/docs`
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Enter parameters/request body
5. Click "Execute"
6. View the response

### 2.2 Authentication (if enabled)

```bash
# Get a token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"user", "password":"pass"}'

# Use token in requests
curl -X GET "http://localhost:8000/customers" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 2.3 Common API Operations

**Create (POST):**
```bash
curl -X POST "http://localhost:8000/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe"
  }'
```

**Read (GET):**
```bash
# Get by ID
curl -X GET "http://localhost:8000/customers/550e8400-e29b-41d4-a716-446655440000"

# List with pagination
curl -X GET "http://localhost:8000/customers?skip=0&limit=10"
```

**Update (PUT/PATCH):**
```bash
curl -X PUT "http://localhost:8000/customers/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jane Doe"}'
```

**Delete (DELETE):**
```bash
curl -X DELETE "http://localhost:8000/customers/550e8400-e29b-41d4-a716-446655440000"
```

### 2.4 Error Handling

The API returns structured error responses:

```json
{
  "detail": "Customer with email 'john@example.com' already exists"
}
```

Common HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Deleted successfully
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `409 Conflict` - Business logic violation (e.g., email exists)
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## 3. Business Logic & Constraints

### 3.1 Automatic Validations

Your generated application enforces these validations automatically:

**Email Uniqueness:**
```bash
# First request succeeds
curl -X POST "http://localhost:8000/customers" \
  -d '{"email":"john@example.com", "full_name":"John"}'
# Returns: 201 Created

# Second request with same email fails
curl -X POST "http://localhost:8000/customers" \
  -d '{"email":"john@example.com", "full_name":"Jane"}'
# Returns: 409 Conflict
```

**Foreign Key Relationships:**
```bash
# Creating cart with non-existent customer fails
curl -X POST "http://localhost:8000/carts" \
  -d '{"customer_id":"00000000-0000-0000-0000-000000000000", "items":[]}'
# Returns: 422 Unprocessable Entity
```

**Stock Constraints:**
```bash
# Ordering more items than available fails
curl -X POST "http://localhost:8000/orders" \
  -d '{
    "customer_id":"...",
    "items":[
      {"product_id":"...", "quantity":100}  # If stock is 50
    ]
  }'
# Returns: 422 Unprocessable Entity - "Insufficient stock"
```

### 3.2 Status Transitions

Different entities have valid status transitions:

**Order Status Flow:**
```
pending_payment → paid → processing → shipped → delivered
                        → cancelled
```

**Cart Status Flow:**
```
open → checked_out
```

---

## 4. Database & Data

### 4.1 Database Access

The application uses SQLAlchemy ORM for database operations:

```python
# In generated code (for reference)
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.customer_repository import CustomerRepository

async def example(db: AsyncSession):
    repo = CustomerRepository(db)

    # Create
    customer = await repo.create(customer_data)

    # Read
    customer = await repo.get(customer_id)
    customers = await repo.list()

    # Update
    customer = await repo.update(customer_id, update_data)

    # Delete
    deleted = await repo.delete(customer_id)
```

### 4.2 Database Migrations

The application includes Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### 4.3 Seeding Data

To add initial data:

```bash
# Option A: Use API
curl -X POST "http://localhost:8000/customers" \
  -d '{...}'

# Option B: SQL script
psql -U user -d database < seeds.sql

# Option C: Python script
python scripts/seed_data.py
```

---

## 5. Development

### 5.1 Project Structure

**Models** (`src/models/`):
- `entities.py` - SQLAlchemy ORM models
- `schemas.py` - Pydantic validation schemas

**Repositories** (`src/repositories/`):
- Data access layer
- SQL query execution
- Transaction management

**Services** (`src/services/`):
- Business logic
- Validation enforcement
- Cross-entity operations

**Routes** (`src/api/routes/`):
- FastAPI endpoints
- Request handling
- Response formatting

### 5.2 Adding Custom Code

You can extend the generated application:

**Adding a new endpoint:**
```python
# In src/api/routes/custom.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/example")
async def custom_endpoint(db: AsyncSession = Depends(get_db)):
    # Your custom logic
    return {"message": "Custom endpoint"}
```

**Adding custom validation:**
```python
# In src/services/custom_service.py
class CustomService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_custom_rule(self, data):
        # Your validation logic
        if not self.meets_criteria(data):
            raise ValueError("Custom validation failed")
```

### 5.3 Testing

Run the included test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=src tests/

# Run integration tests
pytest tests/integration/
```

---

## 6. Deployment

### 6.1 Docker Deployment

The application is containerized and ready for deployment:

```bash
# Build Docker image
docker build -t your-app:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/app" \
  your-app:latest

# Or use docker-compose
docker-compose -f docker-compose.yml up -d
```

### 6.2 Environment Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/app_db

# Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# Monitoring
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=True

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourapp.com
```

### 6.3 Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure database with SSL
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Set up automated backups
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up security headers
- [ ] Test database migrations
- [ ] Review API security

---

## 7. Monitoring & Observability

### 7.1 Health Checks

```bash
# Service health
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics
```

### 7.2 Accessing Grafana Dashboards

If Docker setup includes Grafana:

1. Navigate to `http://localhost:3000`
2. Default credentials: admin / admin
3. View dashboards for:
   - System Overview
   - API Performance
   - Database Performance
   - Business Logic Metrics

### 7.3 Logs

```bash
# View application logs
docker logs your-app-container

# View database logs
docker logs your-app-db

# Stream logs in real-time
docker logs -f your-app-container
```

---

## 8. Troubleshooting

### 8.1 Common Issues

**"Connection refused"**
- Ensure database is running
- Check DATABASE_URL environment variable
- Verify firewall rules

**"Port already in use"**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
API_PORT=8001 python src/main.py
```

**"Database migrations failed"**
```bash
# Check migration status
alembic current

# Rollback to previous version
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "Fix"
```

**"Validation errors"**
- Check request body matches schema
- Verify required fields are present
- Review API documentation at `/docs`

### 8.2 Getting Help

1. **API Documentation**: Visit `/docs` or `/redoc`
2. **Error Messages**: Read detail field in error responses
3. **Logs**: Check application and database logs
4. **Database**: Verify data with SQL query
5. **Status Page**: Check `/health` endpoint

---

## 9. Examples

### 9.1 Complete E-Commerce Flow

```bash
# 1. Create customer
CUSTOMER=$(curl -s -X POST "http://localhost:8000/customers" \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com", "full_name":"John Doe"}' \
  | jq -r '.id')

# 2. View products
curl -s "http://localhost:8000/products?limit=5"

# 3. Create cart
CART=$(curl -s -X POST "http://localhost:8000/carts" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER\", \"items\":[]}" \
  | jq -r '.id')

# 4. Add to cart (via API or business logic)

# 5. Checkout (convert cart to order)

# 6. View order
curl -s "http://localhost:8000/orders"
```

### 9.2 Pagination

```bash
# Get first 20 items
curl "http://localhost:8000/customers?skip=0&limit=20"

# Get next 20
curl "http://localhost:8000/customers?skip=20&limit=20"

# Get last page
curl "http://localhost:8000/customers?skip=40&limit=20"
```

### 9.3 Filtering & Search

```bash
# Some endpoints support filters (check /docs)
curl "http://localhost:8000/orders?status=completed"

curl "http://localhost:8000/customers?search=john"
```

---

## 10. Support & Resources

- **API Documentation**: `http://localhost:8000/docs`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`
- **Health Status**: `http://localhost:8000/health`
- **Metrics**: `http://localhost:8000/metrics`
- **README**: See `README.md` in project root

---

**Owner**: DevMatrix Team
**Updated**: 2025-11-23
**Status**: ✅ **COMPLETE** - Comprehensive user guide created
