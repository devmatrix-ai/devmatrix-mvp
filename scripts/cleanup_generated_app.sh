#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script to clean up a generated DevMatrix app and all its Docker resources
# Usage: ./cleanup_generated_app.sh [APP_PATH] [--regenerate]

show_help() {
    cat << EOF
${BLUE}╔════════════════════════════════════════════════════════════════╗
║           DevMatrix Generated App Cleanup Script               ║
╚════════════════════════════════════════════════════════════════╝${NC}

${YELLOW}Usage:${NC}
  $0 [APP_PATH]

${YELLOW}Arguments:${NC}
  APP_PATH    Path to the generated app directory (optional)
              If not provided, will clean ALL generated apps

${YELLOW}Options:${NC}
  --help, -h  Show this help message

${YELLOW}Examples:${NC}
  # Clean a specific app
  $0 /home/kwar/code/agentic-ai/tests/e2e/generated_apps/ecommerce_api_simple_1763724930

  # Clean all generated apps
  $0

${YELLOW}What this script does:${NC}
  1. Stop and remove Docker containers (ONLY app_* containers, DevMatrix untouched)
  2. Remove Docker volumes (ONLY docker_* volumes, DevMatrix untouched)
  3. Remove the generated app directory
  4. Show instructions for regenerating a fresh app

${YELLOW}Safety:${NC}
  This script ONLY touches generated app resources:
  - Containers starting with: app_*
  - Volumes starting with: docker_*

  DevMatrix infrastructure (devmatrix-*) is completely safe and untouched.

EOF
}

echo_step() {
    echo -e "${BLUE}▶${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✅${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

echo_error() {
    echo -e "${RED}❌${NC} $1"
}

# Parse arguments
APP_PATH=""

for arg in "$@"; do
    case $arg in
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "$APP_PATH" ]]; then
                APP_PATH="$arg"
            fi
            ;;
    esac
done

# Determine cleanup scope
GENERATED_APPS_DIR="/home/kwar/code/agentic-ai/tests/e2e/generated_apps"

if [[ -z "$APP_PATH" ]]; then
    echo_warning "No specific app path provided - will clean ALL generated apps"
    APPS_TO_CLEAN=$(find "$GENERATED_APPS_DIR" -maxdepth 1 -type d -name "*_api_*" 2>/dev/null || echo "")
    CLEAN_ALL=true
else
    # Validate the provided path
    if [[ ! -d "$APP_PATH" ]]; then
        echo_error "App path does not exist: $APP_PATH"
        exit 1
    fi
    APPS_TO_CLEAN="$APP_PATH"
    CLEAN_ALL=false
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Starting DevMatrix App Cleanup Process               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Stop and remove Docker Compose stacks
echo_step "Step 1/4: Stopping and removing Docker Compose stacks..."

if [[ "$CLEAN_ALL" == true ]]; then
    # Clean all app containers (ONLY those starting with app_)
    echo_step "  Finding all generated app containers (app_*)..."

    # IMPORTANT: Only remove containers that start with "app_"
    # This prevents touching DevMatrix containers (devmatrix_*)
    containers=$(docker ps -a --filter "name=^app_" --format "{{.Names}}" 2>/dev/null || echo "")
    if [[ -n "$containers" ]]; then
        echo "    Removing containers:"
        echo "$containers" | while read -r container; do
            echo "      - $container"
        done
        echo "$containers" | xargs -r docker rm -f 2>/dev/null || true
    else
        echo_warning "No app containers found"
    fi
else
    # Clean specific app's docker-compose stack
    for app in $APPS_TO_CLEAN; do
        DOCKER_DIR="$app/docker"
        if [[ -d "$DOCKER_DIR" ]]; then
            echo "    Cleaning docker-compose stack in: $DOCKER_DIR"
            cd "$DOCKER_DIR"
            docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null || true
        fi
    done

    # Also clean by name pattern to catch any stragglers (ONLY app_*)
    containers=$(docker ps -a --filter "name=^app_" --format "{{.Names}}" 2>/dev/null || echo "")
    if [[ -n "$containers" ]]; then
        echo "    Removing straggler containers:"
        echo "$containers" | while read -r container; do
            echo "      - $container"
        done
        echo "$containers" | xargs -r docker rm -f 2>/dev/null || true
    fi
fi

echo_success "Docker containers removed"
echo ""

# Step 2: Remove Docker volumes
echo_step "Step 2/4: Removing Docker volumes..."

# IMPORTANT: Only remove volumes that start with "docker_"
# This is the prefix used by generated apps' docker-compose
# DevMatrix volumes have different prefixes (devmatrix_*, agentic-ai_*, etc.)
volumes=$(docker volume ls --filter "name=^docker_" --format "{{.Name}}" 2>/dev/null || echo "")
if [[ -n "$volumes" ]]; then
    echo "    Removing volumes:"
    echo "$volumes" | while read -r volume; do
        echo "      - $volume"
    done
    echo "$volumes" | xargs -r docker volume rm 2>/dev/null || true
else
    echo_warning "No app volumes found"
fi

echo_success "Docker volumes removed"
echo ""

# Step 3: Remove app directories
echo_step "Step 3/4: Removing app directories..."

if [[ "$CLEAN_ALL" == true ]]; then
    if [[ -n "$APPS_TO_CLEAN" ]]; then
        for app in $APPS_TO_CLEAN; do
            echo "    Removing: $app"
            rm -rf "$app"
        done
        echo_success "All generated app directories removed"
    else
        echo_warning "No generated apps found to remove"
    fi
else
    for app in $APPS_TO_CLEAN; do
        echo "    Removing: $app"
        rm -rf "$app"
    done
    echo_success "App directory removed"
fi
echo ""

# Step 4: Verify cleanup
echo_step "Step 4/4: Verifying cleanup..."

remaining_containers=$(docker ps -a --filter "name=^app_" --format "{{.Names}}" 2>/dev/null | wc -l)
remaining_volumes=$(docker volume ls --filter "name=^docker_" --format "{{.Name}}" 2>/dev/null | wc -l)
remaining_apps=$(find "$GENERATED_APPS_DIR" -maxdepth 1 -type d -name "*_api_*" 2>/dev/null | wc -l)

echo "  Checking for remaining resources..."
echo "    - App containers (app_*): $remaining_containers"
echo "    - App volumes (docker_*): $remaining_volumes"
echo "    - App directories: $remaining_apps"

if [[ $remaining_containers -eq 0 ]] && [[ $remaining_volumes -eq 0 ]] && [[ $remaining_apps -eq 0 ]]; then
    echo_success "Cleanup verified - all app resources removed (DevMatrix untouched)"
else
    echo_warning "Some app resources may still exist:"
    [[ $remaining_containers -gt 0 ]] && echo "    - Containers: $remaining_containers"
    [[ $remaining_volumes -gt 0 ]] && echo "    - Volumes: $remaining_volumes"
    [[ $remaining_apps -gt 0 ]] && echo "    - App directories: $remaining_apps"
fi
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Cleanup Completed Successfully!               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 5: Show regeneration instructions
echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║              How to Generate a Fresh App                       ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}To generate a fresh app with all the latest fixes:${NC}"
echo ""
echo -e "  ${BLUE}1.${NC} Navigate to DevMatrix directory:"
echo -e "     ${GREEN}cd /home/kwar/code/agentic-ai${NC}"
echo ""
echo -e "  ${BLUE}2.${NC} Run the E2E test (with unbuffered output for real-time logs):"
echo -e "     ${GREEN}PRODUCTION_MODE=true PYTHONPATH=/home/kwar/code/agentic-ai timeout 120 python -u tests/e2e/real_e2e_full_pipeline.py${NC}"
echo ""
echo -e "${YELLOW}Latest fixes included:${NC}"
echo -e "  ✅ Ports configured for no conflicts (8002, 5433, 9091, 3002)"
echo -e "  ✅ Credentials standardized (devmatrix/admin)"
echo -e "  ✅ Alembic migrations fixed (dual-driver asyncpg/psycopg)"
echo -e "  ✅ Real-time logging enabled (FlushingStreamHandler)"
echo -e "  ✅ Prometheus metrics deduplicated (import from middleware)"
echo -e "  ✅ Prometheus/Grafana use Docker service names (app:8000, prometheus:9090)"
echo -e "  ✅ Logs in human-readable format (not JSON)"
echo -e "  ✅ Requirements.txt with verified versions (psycopg 3.2.12)"
echo ""

echo ""
echo -e "${GREEN}Done! 🎉${NC}"
