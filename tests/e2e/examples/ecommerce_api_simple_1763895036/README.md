# FastAPI Application

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready FastAPI application featuring e-commerce functionality with products, customers, shopping carts, and order management. Built with async/await support, comprehensive monitoring, and enterprise-grade infrastructure.

## 🎯 Features

### Core Functionality
- **Product Management**: Create, read, update, and deactivate products with inventory tracking
- **Customer Management**: User registration and profile management
- **Shopping Cart**: Add/remove items, manage cart state
- **Order Processing**: Create orders, track status, manage payment workflows
- **Health Checks**: Application health monitoring endpoints

### Technical Features
- ⚡ **Async/Await**: Full async support with FastAPI and SQLAlchemy
- 📊 **Metrics**: Prometheus metrics integration for monitoring
- 🔍 **Structured Logging**: Enterprise-grade logging with structlog
- 🗄️ **Database Migrations**: Alembic for version control of schema changes
- 🧪 **Testing**: Comprehensive test suite with pytest
- 🐳 **Docker Support**: Containerized deployment with Docker Compose
- 📈 **Observability**: Grafana dashboards and Prometheus monitoring
- ✅ **Data Validation**: Pydantic v2 for robust request/response validation

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.104+ |
| **Python** | 3.11+ |
| **Database** | PostgreSQL 15+ |
| **ORM** | SQLAlchemy (async) |
| **Validation** | Pydantic v2 |
| **Migrations** | Alembic |
| **Logging** | structlog |
| **Monitoring** | Prometheus |
| **Visualization** | Grafana |
| **Testing** | pytest |
| **Containerization** | Docker & Docker Compose |
| **Server** | Uvicorn |

## 📋 Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Docker**: 20.10+ (optional, for containerized deployment)
- **Docker Compose**: 2.0+ (optional)
- **pip**: Latest version

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fastapi-application
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application
APP_NAME=FastAPI Application
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fastapi_db
DATABASE_ECHO=False

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Monitoring
PROMETHEUS_ENABLED=True
METRICS_PORT=8001

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
```

### 5. Initialize Database

```bash
# Create database
createdb fastapi_db

# Run migrations
alembic upgrade head
```

## 🗄️ Database Setup

### Create PostgreSQL Database

```bash
# Using psql
psql -U postgres
CREATE DATABASE fastapi_db;
CREATE USER fastapi_user WITH PASSWORD 'secure_password';
ALTER ROLE fastapi_user SET client_encoding TO 'utf8';
ALTER ROLE fastapi_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE fastapi_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE fastapi_db TO fastapi_user;
\q
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## 🏃 Running the Application

### Local Development

```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Using make command (if Makefile available)
make run
```

### Production with Gunicorn

```bash
gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f app

# Stop services
docker-compose -f docker/docker-compose.yml down
```

### Accessing the Application

- **API**: http://localhost:8000
- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8001/metrics (if Prometheus enabled)

## 📚 API Documentation

### Interactive API Documentation

The application provides interactive API documentation powered by Swagger UI and ReDoc:

- **Swagger UI** (http://localhost:8000/docs): Interactive API exploration with try-it-out functionality
- **ReDoc** (http://localhost:8000/redoc): Beautiful, responsive API documentation

### API Endpoints Overview

#### Products
```
POST   /products              - Create a new product
GET    /products              - List all active products
GET    /products/{id}         - Get product details
PUT    /products/{id}         - Update product information
DELETE /products/{id}         - Deactivate a product
```

#### Customers
```
POST   /customers             - Register a new customer
GET    /customers/{id}        - Get customer profile
PUT    /customers/{id}        - Update customer information
```

#### Shopping Cart
```
POST   /carts                 - Create a new cart
GET    /carts/{id}            - View cart contents
POST   /carts/{id}/items      - Add item to cart
DELETE /carts/{id}/items/{item_id} - Remove item from cart
```

#### Orders
```
POST   /orders                - Create a new order
GET    /orders/{id}           - Get order details
GET    /orders                - List customer orders
PUT    /orders/{id}           - Update order status
```

#### Health & Monitoring
```
GET    /health                - Application health status
GET    /metrics               - Prometheus metrics
```

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_products.py
```

### Run Tests in Watch Mode

```bash
pytest-watch
```

### Run Tests with Verbose Output

```bash
pytest -v --tb=short
```

### Test Configuration

Tests use a separate test database. Configure in `.env.test`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fastapi_test_db
DEBUG=True
LOG_LEVEL=DEBUG
```

## 📁 Project Structure

```
fastapi-application/
├── alembic/                          # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── docker/                           # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   ├── prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       └── datasources/
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── cart.py
│   │   │   ├── customer.py
│   │   │   ├── health.py
│   │   │   ├── metrics.py
│   │   │   ├── order.py
│   │   │   └── product.py
│   │   ├── dependencies.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── cart.py
│   │   ├── customer.py
│   │   ├── order.py
│   │   └── product.py
│   ├── services/
│   │   ├── cart_service.py
│   │   ├── customer_service.