#!/bin/bash

# DevMatrix Docker Services Startup Script
# Usage: ./docker/start-services.sh [profile]
# Profiles: all, dev, monitoring, tools

set -e

PROFILE=${1:-all}
PROJECT_NAME="devmatrix"

echo "🚀 Starting DevMatrix services..."
echo "📦 Profile: $PROFILE"
echo ""

# Validate .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Please copy .env.example to .env and update values"
    exit 1
fi

# Build custom images if needed
echo "🔨 Building images..."
docker-compose build --no-cache api 2>/dev/null || true

# Start services based on profile
if [ "$PROFILE" = "all" ]; then
    echo "▶️  Starting all services (core + tools + monitoring)..."
    docker-compose --profile dev --profile tools --profile monitoring up -d
elif [ "$PROFILE" = "dev" ]; then
    echo "▶️  Starting dev profile (core + UI)..."
    docker-compose --profile dev up -d
elif [ "$PROFILE" = "monitoring" ]; then
    echo "▶️  Starting monitoring (Prometheus + Grafana)..."
    docker-compose --profile monitoring up -d
elif [ "$PROFILE" = "tools" ]; then
    echo "▶️  Starting tools (pgAdmin)..."
    docker-compose --profile tools up -d
else
    echo "▶️  Starting core services (no UI, no monitoring)..."
    docker-compose up -d
fi

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service status
SERVICES=(
    "devmatrix-postgres:5432"
    "devmatrix-redis:6379"
    "devmatrix-neo4j:7474"
    "devmatrix-neodash:5005"
    "devmatrix-qdrant:6333"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if docker ps -f "name=$name" --format "{{.Names}}" | grep -q "$name"; then
        echo "✅ $name is running"
    else
        echo "⚠️  $name not running in this profile"
    fi
done

echo ""
echo "🎉 Services started successfully!"
echo ""
echo "📍 Service URLs:"
echo "   Neo4j:        http://localhost:7474"
echo "   NeoDash:      http://localhost:5005"
echo "   Qdrant:       http://localhost:6333"
echo "   PostgreSQL:   localhost:5432"
echo "   Redis:        localhost:6379"
echo ""
if [ "$PROFILE" = "all" ] || [ "$PROFILE" = "dev" ]; then
    echo "   UI (Vite):    http://localhost:3000"
fi
if [ "$PROFILE" = "all" ] || [ "$PROFILE" = "monitoring" ]; then
    echo "   Prometheus:   http://localhost:9090"
    echo "   Grafana:      http://localhost:3001"
fi
if [ "$PROFILE" = "all" ] || [ "$PROFILE" = "tools" ]; then
    echo "   pgAdmin:      http://localhost:5050"
fi
echo ""
echo "💡 Useful commands:"
echo "   View logs:     docker-compose logs -f [service]"
echo "   Stop services: docker-compose down"
echo "   Full cleanup:  docker-compose down -v"
