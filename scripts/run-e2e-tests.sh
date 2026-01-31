#!/bin/bash
# =============================================================================
# E2E Test Runner Script
# =============================================================================
# This script starts the E2E test database and runs the E2E tests.
#
# Usage:
#   ./scripts/run-e2e-tests.sh           # Run all E2E tests
#   ./scripts/run-e2e-tests.sh -v        # Run with verbose output
#   ./scripts/run-e2e-tests.sh -k "test_search"  # Run specific tests
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - Python dependencies installed
#
# =============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.e2e.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up E2E test environment..."
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
}

wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres-e2e pg_isready -U biomedical -d knowledge_platform_e2e > /dev/null 2>&1; then
            log_success "PostgreSQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "PostgreSQL failed to start after $max_attempts seconds"
    return 1
}

wait_for_localstack() {
    log_info "Waiting for LocalStack to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:4567/_localstack/health > /dev/null 2>&1; then
            log_success "LocalStack is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "LocalStack failed to start after $max_attempts seconds"
    return 1
}

# Trap cleanup on exit
trap cleanup EXIT

# Main script
echo ""
echo "=============================================="
echo "   Biomedical Knowledge Platform - E2E Tests  "
echo "=============================================="
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Step 2: Stop any existing E2E containers
log_info "Stopping any existing E2E containers..."
docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

# Step 3: Start E2E services
log_info "Starting E2E test environment..."
docker-compose -f "$COMPOSE_FILE" up -d

# Step 4: Wait for services to be ready
wait_for_postgres
wait_for_localstack

# Step 5: Create S3 buckets in LocalStack
log_info "Creating S3 buckets..."
docker-compose -f "$COMPOSE_FILE" exec -T localstack-e2e awslocal s3 mb s3://biomedical-raw-documents 2>/dev/null || true
docker-compose -f "$COMPOSE_FILE" exec -T localstack-e2e awslocal s3 mb s3://biomedical-processed-chunks 2>/dev/null || true

# Step 6: Run E2E tests
log_info "Running E2E tests..."
echo ""

# Set environment variables for tests
export E2E_DATABASE_URL="postgresql+asyncpg://biomedical:test_password@localhost:5433/knowledge_platform_e2e"
export E2E_S3_ENDPOINT="http://localhost:4567"

# Run pytest with E2E marker
# Pass through any additional arguments (like -v, -k, etc.)
python3 -m pytest tests/e2e/ \
    -m e2e \
    --tb=short \
    --asyncio-mode=auto \
    "$@"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_success "All E2E tests passed!"
else
    log_error "Some E2E tests failed. Exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
