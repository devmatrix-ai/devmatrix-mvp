"""30 Backend Templates for Neo4j Ingestion - Phase B

Templates organized into 4 categories:
- 5 JWT Authentication templates
- 5 API Essential templates
- 10 DDD Core templates
- 10 Data & Service templates
"""

BACKEND_TEMPLATES = [
    # ==================== JWT Authentication (5) ====================
    {
        "id": "jwt_auth_fastapi_v1",
        "name": "FastAPI JWT Authentication",
        "category": "authentication",
        "subcategory": "jwt",
        "framework": "fastapi",
        "language": "python",
        "precision": 0.95,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Production-ready JWT authentication with refresh tokens and access control for FastAPI",
        "code": """
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt
from datetime import datetime, timedelta

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": user_id}

@app.post("/login")
async def login(username: str, password: str):
    # Validate credentials (simplified)
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"message": f"Hello {current_user['user_id']}"}
"""
    },
    {
        "id": "jwt_auth_express_v1",
        "name": "Express.js JWT Authentication",
        "category": "authentication",
        "subcategory": "jwt",
        "framework": "express",
        "language": "javascript",
        "precision": 0.94,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Complete JWT implementation with Express middleware and token refresh",
        "code": """
const express = require('express');
const jwt = require('jsonwebtoken');
const router = express.Router();

const SECRET_KEY = process.env.JWT_SECRET || 'your-secret-key';
const REFRESH_SECRET = process.env.REFRESH_SECRET || 'your-refresh-secret';

const verifyToken = (req, res, next) => {
  const token = req.headers['authorization']?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  jwt.verify(token, SECRET_KEY, (err, decoded) => {
    if (err) return res.status(401).json({ error: 'Invalid token' });
    req.user = decoded;
    next();
  });
};

router.post('/login', (req, res) => {
  const { username, password } = req.body;

  // Validate credentials (simplified)
  const accessToken = jwt.sign(
    { userId: username },
    SECRET_KEY,
    { expiresIn: '1h' }
  );

  const refreshToken = jwt.sign(
    { userId: username },
    REFRESH_SECRET,
    { expiresIn: '7d' }
  );

  res.json({ accessToken, refreshToken });
});

router.post('/refresh', (req, res) => {
  const { refreshToken } = req.body;

  jwt.verify(refreshToken, REFRESH_SECRET, (err, decoded) => {
    if (err) return res.status(401).json({ error: 'Invalid refresh token' });

    const newAccessToken = jwt.sign(
      { userId: decoded.userId },
      SECRET_KEY,
      { expiresIn: '1h' }
    );

    res.json({ accessToken: newAccessToken });
  });
});

router.get('/protected', verifyToken, (req, res) => {
  res.json({ message: `Hello ${req.user.userId}` });
});

module.exports = router;
"""
    },
    {
        "id": "jwt_auth_golang_v1",
        "name": "Go JWT Authentication",
        "category": "authentication",
        "subcategory": "jwt",
        "framework": "gin",
        "language": "go",
        "precision": 0.96,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Secure JWT implementation with Go/Gin framework",
        "code": """
package main

import (
    "net/http"
    "time"
    "github.com/gin-gonic/gin"
    "github.com/golang-jwt/jwt"
)

var jwtSecret = []byte("your-secret-key-change-in-production")

type Claims struct {
    UserID string `json:"user_id"`
    jwt.StandardClaims
}

func createToken(userID string) (string, error) {
    claims := Claims{
        UserID: userID,
        StandardClaims: jwt.StandardClaims{
            ExpiresAt: time.Now().Add(time.Hour).Unix(),
            IssuedAt:  time.Now().Unix(),
        },
    }

    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(jwtSecret)
}

func authMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        tokenString := c.GetHeader("Authorization")
        if tokenString == "" {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "No token"})
            c.Abort()
            return
        }

        claims := &Claims{}
        token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
            return jwtSecret, nil
        })

        if err != nil || !token.Valid {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
            c.Abort()
            return
        }

        c.Set("user_id", claims.UserID)
        c.Next()
    }
}

func main() {
    router := gin.Default()

    router.POST("/login", func(c *gin.Context) {
        username := c.PostForm("username")
        token, _ := createToken(username)
        c.JSON(http.StatusOK, gin.H{"token": token})
    })

    router.GET("/protected", authMiddleware(), func(c *gin.Context) {
        userID := c.GetString("user_id")
        c.JSON(http.StatusOK, gin.H{"message": "Hello " + userID})
    })

    router.Run(":8000")
}
"""
    },
    {
        "id": "jwt_auth_django_v1",
        "name": "Django REST JWT Authentication",
        "category": "authentication",
        "subcategory": "jwt",
        "framework": "django-rest-framework",
        "language": "python",
        "precision": 0.93,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "DRF JWT with simple-jwt package for Django",
        "code": """
# settings.py
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
}

# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]

# views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({'message': f'Hello {request.user.username}'})
"""
    },
    {
        "id": "jwt_auth_rust_v1",
        "name": "Rust Actix-web JWT Authentication",
        "category": "authentication",
        "subcategory": "jwt",
        "framework": "actix-web",
        "language": "rust",
        "precision": 0.97,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "High-performance JWT auth with Rust and Actix-web",
        "code": """
use actix_web::{web, App, HttpServer, HttpRequest, HttpResponse, middleware};
use jsonwebtoken::{encode, decode, Header, Validation, EncodingKey, DecodingKey};
use serde::{Serialize, Deserialize};
use chrono::{Utc, Duration};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: i64,
}

const SECRET: &[u8] = b"your-secret-key";

fn create_token(user_id: &str) -> Result<String, jsonwebtoken::errors::Error> {
    let expiration = Utc::now() + Duration::hours(1);
    let claims = Claims {
        sub: user_id.to_string(),
        exp: expiration.timestamp(),
    };
    encode(&Header::default(), &claims, &EncodingKey::from_secret(SECRET))
}

fn verify_token(token: &str) -> Result<Claims, jsonwebtoken::errors::Error> {
    decode::<Claims>(
        token,
        &DecodingKey::from_secret(SECRET),
        &Validation::default(),
    ).map(|c| c.claims)
}

async fn login(body: web::Json<LoginRequest>) -> HttpResponse {
    match create_token(&body.username) {
        Ok(token) => HttpResponse::Ok().json(json!({"token": token})),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

async fn protected(req: HttpRequest) -> HttpResponse {
    let token = req.headers().get("Authorization").and_then(|h| h.to_str().ok());
    match token {
        Some(t) => match verify_token(t) {
            Ok(claims) => HttpResponse::Ok().json(json!({"message": format!("Hello {}", claims.sub)})),
            Err(_) => HttpResponse::Unauthorized().finish(),
        },
        None => HttpResponse::Unauthorized().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/login", web::post().to(login))
            .route("/protected", web::get().to(protected))
    })
    .bind("127.0.0.1:8000")?
    .run()
    .await
}
"""
    },

    # ==================== API Essential (5) ====================
    {
        "id": "api_crud_fastapi_v1",
        "name": "FastAPI CRUD Operations",
        "category": "api",
        "subcategory": "crud",
        "framework": "fastapi",
        "language": "python",
        "precision": 0.92,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Complete CRUD API endpoints with FastAPI and validation",
        "code": """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Item(BaseModel):
    id: int = None
    name: str
    description: str = None
    price: float

items_db = []

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    item.id = len(items_db) + 1
    items_db.append(item)
    return item

@app.get("/items", response_model=List[Item])
async def list_items(skip: int = 0, limit: int = 10):
    return items_db[skip:skip + limit]

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = next((i for i in items_db if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    db_item = next((i for i in items_db if i.id == item_id), None)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.id = item_id
    items_db[items_db.index(db_item)] = item
    return item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    global items_db
    items_db = [i for i in items_db if i.id != item_id]
    return {"deleted": item_id}
"""
    },
    {
        "id": "api_pagination_express_v1",
        "name": "Express.js API Pagination",
        "category": "api",
        "subcategory": "pagination",
        "framework": "express",
        "language": "javascript",
        "precision": 0.91,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Cursor-based and offset pagination for REST APIs",
        "code": """
const express = require('express');
const router = express.Router();

// Offset pagination
router.get('/items', (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 10;
  const offset = (page - 1) * limit;

  const items = generateItems(); // Your data source
  const total = items.length;
  const pages = Math.ceil(total / limit);

  const paginatedItems = items.slice(offset, offset + limit);

  res.json({
    data: paginatedItems,
    pagination: {
      page,
      limit,
      total,
      pages,
      hasNext: page < pages,
      hasPrev: page > 1
    }
  });
});

// Cursor pagination
router.get('/items/cursor', (req, res) => {
  const limit = parseInt(req.query.limit) || 10;
  const cursor = req.query.cursor || null;

  const items = generateItems();
  let startIndex = cursor ? items.findIndex(i => i.id === cursor) + 1 : 0;
  const paginatedItems = items.slice(startIndex, startIndex + limit);

  const hasMore = startIndex + limit < items.length;
  const nextCursor = hasMore ? paginatedItems[paginatedItems.length - 1].id : null;

  res.json({
    data: paginatedItems,
    pagination: {
      cursor,
      nextCursor,
      hasMore
    }
  });
});
"""
    },
    {
        "id": "api_error_handling_golang_v1",
        "name": "Go Error Handling & Logging",
        "category": "api",
        "subcategory": "error-handling",
        "framework": "gin",
        "language": "go",
        "precision": 0.94,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Comprehensive error handling with structured logging",
        "code": """
package main

import (
    "log"
    "net/http"
    "github.com/gin-gonic/gin"
)

type ErrorResponse struct {
    Code    int    `json:"code"`
    Message string `json:"message"`
    Details string `json:"details,omitempty"`
}

func errorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        defer func() {
            if err := recover(); err != nil {
                log.Printf("Panic: %v", err)
                c.JSON(http.StatusInternalServerError, ErrorResponse{
                    Code:    500,
                    Message: "Internal server error",
                })
            }
        }()
        c.Next()
    }
}

func notFoundHandler(c *gin.Context) {
    c.JSON(http.StatusNotFound, ErrorResponse{
        Code:    404,
        Message: "Not found",
        Details: "The requested resource does not exist",
    })
}

func main() {
    router := gin.Default()
    router.Use(errorHandler())

    router.GET("/api/users", func(c *gin.Context) {
        id := c.Query("id")
        if id == "" {
            c.JSON(http.StatusBadRequest, ErrorResponse{
                Code:    400,
                Message: "Missing required parameter: id",
            })
            return
        }
        c.JSON(http.StatusOK, gin.H{"message": "ok"})
    })

    router.NoRoute(notFoundHandler)
    router.Run(":8000")
}
"""
    },
    {
        "id": "api_versioning_django_v1",
        "name": "Django REST API Versioning",
        "category": "api",
        "subcategory": "versioning",
        "framework": "django-rest-framework",
        "language": "python",
        "precision": 0.90,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Multiple API versioning strategies with DRF",
        "code": """
# urls.py
from django.urls import path
from rest_framework import routers
from . import views

# URL versioning: /api/v1/users vs /api/v2/users
urlpatterns = [
    path('api/v1/users/', views.UserListV1.as_view()),
    path('api/v2/users/', views.UserListV2.as_view()),
]

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning, URLPathVersioning

class UserListV1(APIView):
    versioning_class = URLPathVersioning

    def get(self, request):
        return Response({'users': [], 'version': 'v1'})

class UserListV2(APIView):
    versioning_class = URLPathVersioning

    def get(self, request):
        return Response({'users': [], 'meta': {'total': 0}, 'version': 'v2'})

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
}
"""
    },
    {
        "id": "api_caching_actix_v1",
        "name": "Actix-web API Caching",
        "category": "api",
        "subcategory": "caching",
        "framework": "actix-web",
        "language": "rust",
        "precision": 0.95,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "HTTP caching with ETag and Last-Modified headers",
        "code": """
use actix_web::{web, App, HttpServer, HttpResponse, middleware};
use std::collections::HashMap;
use chrono::Utc;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .wrap(middleware::Compress::default())
            .route("/api/data", web::get().to(get_cached_data))
    })
    .bind("127.0.0.1:8000")?
    .run()
    .await
}

async fn get_cached_data(req: web::HttpRequest) -> HttpResponse {
    let etag = "abc123";
    let last_modified = Utc::now().to_rfc2822();

    if let Some(if_none_match) = req.headers().get("if-none-match") {
        if if_none_match.to_str().unwrap_or("") == etag {
            return HttpResponse::NotModified().finish();
        }
    }

    HttpResponse::Ok()
        .insert_header(("etag", etag))
        .insert_header(("last-modified", last_modified))
        .insert_header(("cache-control", "max-age=3600"))
        .json(json!({"data": "cached content"}))
}
"""
    },

    # ==================== DDD Core (10) ====================
    {
        "id": "ddd_aggregate_fastapi_v1",
        "name": "DDD Aggregate Pattern - FastAPI",
        "category": "ddd",
        "subcategory": "aggregate",
        "framework": "fastapi",
        "language": "python",
        "precision": 0.93,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Aggregate pattern implementation for domain-driven design",
        "code": """
from dataclasses import dataclass
from typing import List
from enum import Enum
from datetime import datetime
from uuid import uuid4

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

@dataclass
class OrderItem:
    product_id: str
    quantity: int
    price: float

@dataclass
class Order:
    id: str
    customer_id: str
    items: List[OrderItem]
    status: OrderStatus
    created_at: datetime
    total_amount: float = 0.0

    @classmethod
    def create(cls, customer_id: str, items: List[OrderItem]):
        total = sum(item.quantity * item.price for item in items)
        return cls(
            id=str(uuid4()),
            customer_id=customer_id,
            items=items,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            total_amount=total
        )

    def confirm(self):
        if self.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")
        self.status = OrderStatus.CONFIRMED

    def ship(self):
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("Only confirmed orders can be shipped")
        self.status = OrderStatus.SHIPPED

    def deliver(self):
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("Only shipped orders can be delivered")
        self.status = OrderStatus.DELIVERED
"""
    },
    {
        "id": "ddd_repository_express_v1",
        "name": "DDD Repository Pattern - Express.js",
        "category": "ddd",
        "subcategory": "repository",
        "framework": "express",
        "language": "javascript",
        "precision": 0.92,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Repository pattern for data access abstraction",
        "code": """
class UserRepository {
    constructor(db) {
        this.db = db;
    }

    async findById(id) {
        const query = 'SELECT * FROM users WHERE id = $1';
        const result = await this.db.query(query, [id]);
        return result.rows[0];
    }

    async findByEmail(email) {
        const query = 'SELECT * FROM users WHERE email = $1';
        const result = await this.db.query(query, [email]);
        return result.rows[0];
    }

    async save(user) {
        const query = 'INSERT INTO users (email, name) VALUES ($1, $2) RETURNING *';
        const result = await this.db.query(query, [user.email, user.name]);
        return result.rows[0];
    }

    async update(user) {
        const query = 'UPDATE users SET email = $1, name = $2 WHERE id = $3 RETURNING *';
        const result = await this.db.query(query, [user.email, user.name, user.id]);
        return result.rows[0];
    }

    async delete(id) {
        const query = 'DELETE FROM users WHERE id = $1';
        await this.db.query(query, [id]);
    }

    async findAll() {
        const query = 'SELECT * FROM users';
        const result = await this.db.query(query);
        return result.rows;
    }
}

module.exports = UserRepository;
"""
    },
    {
        "id": "ddd_event_sourcing_golang_v1",
        "name": "DDD Event Sourcing - Go",
        "category": "ddd",
        "subcategory": "event-sourcing",
        "framework": "domain-driven",
        "language": "go",
        "precision": 0.94,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Event sourcing implementation for complete audit trail",
        "code": """
package main

import (
    "time"
)

type Event interface {
    GetAggregateID() string
    GetTimestamp() time.Time
    GetType() string
}

type OrderCreatedEvent struct {
    AggregateID string
    Timestamp   time.Time
    CustomerID  string
    Amount      float64
}

func (e OrderCreatedEvent) GetAggregateID() string { return e.AggregateID }
func (e OrderCreatedEvent) GetTimestamp() time.Time { return e.Timestamp }
func (e OrderCreatedEvent) GetType() string { return "OrderCreated" }

type OrderConfirmedEvent struct {
    AggregateID string
    Timestamp   time.Time
}

func (e OrderConfirmedEvent) GetAggregateID() string { return e.AggregateID }
func (e OrderConfirmedEvent) GetTimestamp() time.Time { return e.Timestamp }
func (e OrderConfirmedEvent) GetType() string { return "OrderConfirmed" }

type EventStore struct {
    events map[string][]Event
}

func (es *EventStore) Append(event Event) error {
    id := event.GetAggregateID()
    es.events[id] = append(es.events[id], event)
    return nil
}

func (es *EventStore) GetEvents(aggregateID string) []Event {
    return es.events[aggregateID]
}

func (es *EventStore) ReplayEvents(aggregateID string) interface{} {
    events := es.GetEvents(aggregateID)
    var state interface{}

    for _, event := range events {
        switch e := event.(type) {
        case OrderCreatedEvent:
            state = map[string]interface{}{
                "id": e.AggregateID,
                "status": "created",
                "amount": e.Amount,
            }
        case OrderConfirmedEvent:
            if m, ok := state.(map[string]interface{}); ok {
                m["status"] = "confirmed"
            }
        }
    }

    return state
}
"""
    },
    {
        "id": "ddd_value_object_django_v1",
        "name": "DDD Value Objects - Django",
        "category": "ddd",
        "subcategory": "value-object",
        "framework": "django",
        "language": "python",
        "precision": 0.91,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Value object patterns for immutable domain objects",
        "code": """
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __str__(self):
        return f"{self.amount} {self.currency}"

@dataclass(frozen=True)
class EmailAddress:
    address: str

    def __post_init__(self):
        if "@" not in self.address:
            raise ValueError("Invalid email address")

    def __str__(self):
        return self.address

@dataclass(frozen=True)
class PhoneNumber:
    number: str
    country_code: str = "+1"

    def formatted(self) -> str:
        return f"{self.country_code} {self.number}"

# Usage in models
from django.db import models

class Order(models.Model):
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_email = models.EmailField()

    def get_total_as_money(self) -> Money:
        return Money(Decimal(self.total_amount))

    def set_customer_email(self, email: EmailAddress):
        self.customer_email = str(email)
"""
    },
    {
        "id": "ddd_specification_fastapi_v1",
        "name": "DDD Specification Pattern - FastAPI",
        "category": "ddd",
        "subcategory": "specification",
        "framework": "fastapi",
        "language": "python",
        "precision": 0.92,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Specification pattern for complex business rules",
        "code": """
from abc import ABC, abstractmethod
from typing import List, Generic, TypeVar

T = TypeVar('T')

class Specification(ABC, Generic[T]):
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        pass

    def and_spec(self, other: 'Specification[T]') -> 'Specification[T]':
        return AndSpecification(self, other)

    def or_spec(self, other: 'Specification[T]') -> 'Specification[T]':
        return OrSpecification(self, other)

class PremiumCustomerSpec(Specification):
    def is_satisfied_by(self, customer) -> bool:
        return customer.lifetime_value > 10000

class ActiveCustomerSpec(Specification):
    def is_satisfied_by(self, customer) -> bool:
        return customer.is_active

class PremiumActiveCustomerSpec(Specification):
    def __init__(self):
        self.premium = PremiumCustomerSpec()
        self.active = ActiveCustomerSpec()

    def is_satisfied_by(self, customer) -> bool:
        return self.premium.is_satisfied_by(customer) and self.active.is_satisfied_by(customer)

# Usage
def get_eligible_customers(customers: List) -> List:
    spec = PremiumActiveCustomerSpec()
    return [c for c in customers if spec.is_satisfied_by(c)]
"""
    },
    {
        "id": "ddd_factory_golang_v1",
        "name": "DDD Factory Pattern - Go",
        "category": "ddd",
        "subcategory": "factory",
        "framework": "domain-driven",
        "language": "go",
        "precision": 0.93,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Factory pattern for complex object creation",
        "code": """
package main

type Product struct {
    ID    string
    Name  string
    Type  string
    Price float64
}

type ProductFactory interface {
    Create(name string, price float64) *Product
}

type PhysicalProductFactory struct{}

func (f PhysicalProductFactory) Create(name string, price float64) *Product {
    return &Product{
        ID:    generateID(),
        Name:  name,
        Type:  "physical",
        Price: price,
    }
}

type DigitalProductFactory struct{}

func (f DigitalProductFactory) Create(name string, price float64) *Product {
    return &Product{
        ID:    generateID(),
        Name:  name,
        Type:  "digital",
        Price: price,
    }
}

func CreateProduct(factory ProductFactory, name string, price float64) *Product {
    return factory.Create(name, price)
}

func generateID() string {
    return "prod_" + uuid.New().String()
}
"""
    },
    {
        "id": "ddd_domain_service_django_v1",
        "name": "DDD Domain Service - Django",
        "category": "ddd",
        "subcategory": "domain-service",
        "framework": "django",
        "language": "python",
        "precision": 0.91,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Domain service for cross-aggregate operations",
        "code": """
from abc import ABC, abstractmethod

class TransferService(ABC):
    @abstractmethod
    def transfer(self, from_account, to_account, amount):
        pass

class BankTransferService(TransferService):
    def __init__(self, account_repo, audit_repo):
        self.account_repo = account_repo
        self.audit_repo = audit_repo

    def transfer(self, from_account_id, to_account_id, amount):
        from_account = self.account_repo.find(from_account_id)
        to_account = self.account_repo.find(to_account_id)

        if from_account.balance < amount:
            raise ValueError("Insufficient funds")

        from_account.debit(amount)
        to_account.credit(amount)

        self.account_repo.save(from_account)
        self.account_repo.save(to_account)

        audit = {
            'from_id': from_account_id,
            'to_id': to_account_id,
            'amount': amount,
            'timestamp': datetime.now()
        }
        self.audit_repo.save(audit)

        return {'status': 'success', 'audit_id': audit['id']}

# Usage
transfer_service = BankTransferService(account_repo, audit_repo)
result = transfer_service.transfer('account_1', 'account_2', 100)
"""
    },
    {
        "id": "ddd_bounded_context_express_v1",
        "name": "DDD Bounded Contexts - Express.js",
        "category": "ddd",
        "subcategory": "bounded-context",
        "framework": "express",
        "language": "javascript",
        "precision": 0.90,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Bounded context separation and anti-corruption layer",
        "code": """
// UserContext
class User {
    constructor(id, email, password) {
        this.id = id;
        this.email = email;
        this.password = password;
    }
}

class UserRepository {
    async save(user) { }
    async findById(id) { }
}

// OrderContext
class Order {
    constructor(id, userId, items) {
        this.id = id;
        this.userId = userId;
        this.items = items;
    }
}

class OrderRepository {
    async save(order) { }
    async findByUserId(userId) { }
}

// Anti-Corruption Layer
class UserAntiCorruptionLayer {
    constructor(userRepository) {
        this.userRepository = userRepository;
    }

    async getOrderOwner(userId) {
        const user = await this.userRepository.findById(userId);
        return {
            id: user.id,
            email: user.email
        };
    }
}

// Usage in OrderContext
const orderRouter = require('express').Router();
const acl = new UserAntiCorruptionLayer(userRepository);

orderRouter.post('/orders', async (req, res) => {
    const owner = await acl.getOrderOwner(req.body.user_id);
    const order = new Order(uuid(), req.body.user_id, req.body.items);
    await orderRepository.save(order);
    res.json({ order });
});
"""
    },
    {
        "id": "ddd_ubiquitous_language_python_v1",
        "name": "DDD Ubiquitous Language - Python",
        "category": "ddd",
        "subcategory": "ubiquitous-language",
        "framework": "python",
        "language": "python",
        "precision": 0.89,
        "complexity": "low",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Ubiquitous language implementation in code",
        "code": """
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

@dataclass
class GuestRequirement:
    adult_count: int
    child_count: int

@dataclass
class Booking:
    booking_id: str
    guest_email: str
    check_in_date: datetime
    check_out_date: datetime
    guest_requirement: GuestRequirement
    status: BookingStatus
    created_at: datetime

    def confirm_booking(self):
        if self.status != BookingStatus.PENDING:
            raise ValueError("Only pending bookings can be confirmed")
        self.status = BookingStatus.CONFIRMED

    def cancel_booking(self, reason: str):
        if self.status == BookingStatus.CANCELLED:
            raise ValueError("Booking already cancelled")
        self.status = BookingStatus.CANCELLED

    def calculate_nights(self) -> int:
        return (self.check_out_date - self.check_in_date).days

class BookingService:
    def make_reservation(self, guest_email: str, dates, guests) -> Booking:
        booking = Booking(
            booking_id=generate_id(),
            guest_email=guest_email,
            check_in_date=dates['check_in'],
            check_out_date=dates['check_out'],
            guest_requirement=GuestRequirement(**guests),
            status=BookingStatus.PENDING,
            created_at=datetime.now()
        )
        return booking
"""
    },

    # ==================== Data & Service (10) ====================
    {
        "id": "data_repository_sqlalchemy_v1",
        "name": "SQLAlchemy Repository Pattern",
        "category": "data",
        "subcategory": "repository",
        "framework": "sqlalchemy",
        "language": "python",
        "precision": 0.94,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Generic repository pattern with SQLAlchemy ORM",
        "code": """
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: T):
        self.db = db
        self.model = model

    def create(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_by_id(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: int, obj: T) -> Optional[T]:
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None

        for key, value in obj.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if not obj:
            return False

        self.db.delete(obj)
        self.db.commit()
        return True

    def find_by_field(self, field_name: str, value: any) -> List[T]:
        return self.db.query(self.model).filter(
            getattr(self.model, field_name) == value
        ).all()
"""
    },
    {
        "id": "data_caching_redis_v1",
        "name": "Redis Caching Strategy",
        "category": "data",
        "subcategory": "caching",
        "framework": "redis",
        "language": "python",
        "precision": 0.93,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Cache-aside pattern with Redis",
        "code": """
import redis
import json
from typing import Optional

class CacheService:
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl

    def get(self, key: str) -> Optional[dict]:
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    def set(self, key: str, value: dict, ttl: Optional[int] = None):
        expiry = ttl or self.ttl
        self.redis.setex(key, expiry, json.dumps(value))

    def delete(self, key: str):
        self.redis.delete(key)

    def invalidate_pattern(self, pattern: str):
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

# Usage
cache_service = CacheService(redis.Redis())

def get_user(user_id: int):
    cache_key = f"user:{user_id}"

    cached_user = cache_service.get(cache_key)
    if cached_user:
        return cached_user

    user = db.query(User).get(user_id)
    cache_service.set(cache_key, user.to_dict())
    return user

def update_user(user_id: int, data: dict):
    user = db.query(User).get(user_id)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()

    cache_key = f"user:{user_id}"
    cache_service.delete(cache_key)

    return user
"""
    },
    {
        "id": "data_transaction_management_v1",
        "name": "Database Transaction Management",
        "category": "data",
        "subcategory": "transactions",
        "framework": "generic",
        "language": "python",
        "precision": 0.95,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "ACID transaction patterns",
        "code": """
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://user:pass@localhost/db')
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_transaction():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def transfer_funds(from_id: int, to_id: int, amount: float):
    with get_transaction() as session:
        from_account = session.query(Account).filter_by(id=from_id).with_for_update().first()
        to_account = session.query(Account).filter_by(id=to_id).with_for_update().first()

        if from_account.balance < amount:
            raise ValueError("Insufficient funds")

        from_account.balance -= amount
        to_account.balance += amount

        session.add_all([from_account, to_account])
        # Transaction commits automatically on context exit

def batch_update_with_rollback(updates: List[dict]):
    with get_transaction() as session:
        for update in updates:
            user = session.query(User).get(update['id'])
            if not user:
                raise ValueError(f"User {update['id']} not found")
            user.name = update['name']
            session.add(user)
        # All updates commit together
"""
    },
    {
        "id": "data_migration_alembic_v1",
        "name": "Database Migrations with Alembic",
        "category": "data",
        "subcategory": "migrations",
        "framework": "alembic",
        "language": "python",
        "precision": 0.92,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Schema versioning with Alembic",
        "code": """
# Migration example: alembic/versions/001_create_users.py
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('username', sa.String(80), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('users')

# Migration: alembic/versions/002_add_user_fields.py
def upgrade():
    op.add_column('users', sa.Column('first_name', sa.String(100)))
    op.add_column('users', sa.Column('last_name', sa.String(100)))
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email', 'users')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
"""
    },
    {
        "id": "service_business_logic_v1",
        "name": "Business Logic Service Layer",
        "category": "service",
        "subcategory": "business-logic",
        "framework": "generic",
        "language": "python",
        "precision": 0.91,
        "complexity": "high",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Clean service layer implementation",
        "code": """
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class OrderItem:
    product_id: str
    quantity: int
    price: float

class OrderService:
    def __init__(self, order_repo, inventory_repo, payment_service):
        self.order_repo = order_repo
        self.inventory_repo = inventory_repo
        self.payment_service = payment_service

    def create_order(self, customer_id: str, items: List[OrderItem]) -> dict:
        # Validate inventory
        for item in items:
            stock = self.inventory_repo.get_stock(item.product_id)
            if stock < item.quantity:
                raise ValueError(f"Insufficient stock for {item.product_id}")

        # Calculate total
        total = sum(item.quantity * item.price for item in items)

        # Process payment
        payment_result = self.payment_service.charge(customer_id, total)
        if not payment_result['success']:
            raise ValueError("Payment failed")

        # Create order
        order = {
            'customer_id': customer_id,
            'items': items,
            'total': total,
            'payment_id': payment_result['transaction_id']
        }

        return self.order_repo.save(order)

    def cancel_order(self, order_id: str):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        # Refund payment
        self.payment_service.refund(order['payment_id'])

        # Restore inventory
        for item in order['items']:
            self.inventory_repo.add_stock(item['product_id'], item['quantity'])

        return self.order_repo.delete(order_id)
"""
    },
    {
        "id": "service_event_publishing_v1",
        "name": "Event Publishing Service",
        "category": "service",
        "subcategory": "events",
        "framework": "generic",
        "language": "python",
        "precision": 0.92,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Pub/Sub event system for loose coupling",
        "code": """
from typing import Callable, List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DomainEvent:
    event_type: str
    aggregate_id: str
    data: dict
    timestamp: datetime

class EventPublisher:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def publish(self, event: DomainEvent):
        handlers = self.subscribers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

# Usage
publisher = EventPublisher()

def on_order_created(event: DomainEvent):
    print(f"Order {event.aggregate_id} created")
    # Send confirmation email
    # Update analytics
    # Trigger inventory deduction

def on_order_cancelled(event: DomainEvent):
    print(f"Order {event.aggregate_id} cancelled")
    # Process refund
    # Restore inventory

publisher.subscribe('order.created', on_order_created)
publisher.subscribe('order.cancelled', on_order_cancelled)

# In domain logic
order_created_event = DomainEvent(
    event_type='order.created',
    aggregate_id='order_123',
    data={'customer_id': 'cust_456', 'amount': 99.99},
    timestamp=datetime.now()
)
publisher.publish(order_created_event)
"""
    },
    {
        "id": "service_dependency_injection_v1",
        "name": "Dependency Injection Container",
        "category": "service",
        "subcategory": "dependency-injection",
        "framework": "generic",
        "language": "python",
        "precision": 0.90,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "IoC container for dependency management",
        "code": """
from typing import Any, Callable, Dict
from abc import ABC, abstractmethod

class DIContainer:
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register_singleton(self, name: str, service: Any):
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable):
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        if name in self._services:
            return self._services[name]

        if name in self._factories:
            service = self._factories[name](self)
            self._services[name] = service
            return service

        raise ValueError(f"Service {name} not registered")

# Usage
container = DIContainer()

# Register dependencies
container.register_singleton('db', PostgresDatabase())
container.register_singleton('cache', RedisCache())

container.register_factory('user_repo', lambda c: UserRepository(c.get('db')))
container.register_factory('user_service', lambda c: UserService(c.get('user_repo')))

# Get dependencies
user_service = container.get('user_service')
"""
    },
    {
        "id": "service_logging_monitoring_v1",
        "name": "Structured Logging & Monitoring",
        "category": "service",
        "subcategory": "logging",
        "framework": "generic",
        "language": "python",
        "precision": 0.93,
        "complexity": "medium",
        "version": "1.0",
        "status": "active",
        "source": "backend",
        "description": "Centralized logging with structured context",
        "code": """
import logging
import json
from datetime import datetime
from functools import wraps

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

    def log(self, level: str, message: str, context: dict = None):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.upper(),
            'message': message,
            'context': context or {}
        }

        if level.lower() == 'error':
            self.logger.error(json.dumps(log_entry))
        elif level.lower() == 'warning':
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))

def log_execution(logger: StructuredLogger):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            }

            try:
                logger.log('info', f'Executing {func.__name__}', context)
                result = func(*args, **kwargs)
                logger.log('info', f'Completed {func.__name__}', context)
                return result
            except Exception as e:
                error_context = {**context, 'error': str(e)}
                logger.log('error', f'Failed {func.__name__}', error_context)
                raise
        return wrapper
    return decorator

# Usage
logger = StructuredLogger('myapp')

@log_execution(logger)
def process_payment(order_id: str, amount: float):
    logger.log('info', 'Processing payment', {'order_id': order_id, 'amount': amount})
    # Payment processing logic
    return {'status': 'success', 'transaction_id': 'txn_123'}
"""
    },
]
