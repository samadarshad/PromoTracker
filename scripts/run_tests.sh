#!/bin/bash
# Main test runner script for PromoTracker
# Runs unit, integration, and e2e tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_CONFIG_FILE="$PROJECT_ROOT/tests/.test-config.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running PromoTracker Tests"
echo "=============================="
echo ""

# Parse command line arguments
DEPLOY_STACK=true
CLEANUP_STACK=false
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_E2E=false
KEEP_STACK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-deploy)
            DEPLOY_STACK=false
            shift
            ;;
        --cleanup)
            CLEANUP_STACK=true
            shift
            ;;
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_E2E=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_E2E=true
            shift
            ;;
        --keep-stack)
            KEEP_STACK=true
            CLEANUP_STACK=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-deploy] [--cleanup] [--unit-only] [--integration] [--e2e] [--all] [--keep-stack]"
            exit 1
            ;;
    esac
done

# Check if virtual environment exists for tests
if [ ! -d "$PROJECT_ROOT/tests/.venv" ]; then
    echo "📦 Creating virtual environment for tests..."
    python3 -m venv "$PROJECT_ROOT/tests/.venv"
    source "$PROJECT_ROOT/tests/.venv/bin/activate"
    pip install -q -r "$PROJECT_ROOT/tests/requirements.txt"
else
    source "$PROJECT_ROOT/tests/.venv/bin/activate"
fi

# Deploy test stack if needed
if [ "$DEPLOY_STACK" = true ] && [ "$RUN_INTEGRATION" = true ] || [ "$RUN_E2E" = true ]; then
    if [ ! -f "$TEST_CONFIG_FILE" ]; then
        echo "⚠️  Test stack not deployed. Deploying now..."
        "$SCRIPT_DIR/deploy_test_stack.sh"
    else
        echo "✅ Test stack already deployed (using existing configuration)"
        echo "   To redeploy, run: ./scripts/deploy_test_stack.sh"
    fi
    echo ""
fi

# Change to project root for pytest
cd "$PROJECT_ROOT"

# Run tests based on flags
TEST_FAILED=false

if [ "$RUN_UNIT" = true ]; then
    echo "📝 Running Unit Tests..."
    echo "----------------------"
    if pytest tests/unit/ -v -m unit --cov-report=term-missing; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        TEST_FAILED=true
    fi
    echo ""
fi

if [ "$RUN_INTEGRATION" = true ]; then
    if [ ! -f "$TEST_CONFIG_FILE" ]; then
        echo -e "${YELLOW}⚠️  Skipping integration tests: test stack not deployed${NC}"
        echo "   Run with --no-integration or deploy stack first"
    else
        echo "🔗 Running Integration Tests..."
        echo "------------------------------"
        if pytest tests/integration/ -v -m integration; then
            echo -e "${GREEN}✅ Integration tests passed${NC}"
        else
            echo -e "${RED}❌ Integration tests failed${NC}"
            TEST_FAILED=true
        fi
    fi
    echo ""
fi

if [ "$RUN_E2E" = true ]; then
    if [ ! -f "$TEST_CONFIG_FILE" ]; then
        echo -e "${YELLOW}⚠️  Skipping e2e tests: test stack not deployed${NC}"
        echo "   Run with --no-e2e or deploy stack first"
    else
        echo "🚀 Running End-to-End Tests..."
        echo "-----------------------------"
        if pytest tests/e2e/ -v -m e2e; then
            echo -e "${GREEN}✅ End-to-end tests passed${NC}"
        else
            echo -e "${RED}❌ End-to-end tests failed${NC}"
            TEST_FAILED=true
        fi
    fi
    echo ""
fi

# Generate coverage report
echo "📊 Test Coverage Report"
echo "----------------------"
echo "HTML coverage report generated at: htmlcov/index.html"
echo ""

# Cleanup test stack if requested
if [ "$CLEANUP_STACK" = true ] && [ -f "$TEST_CONFIG_FILE" ]; then
    echo "🧹 Cleaning up test stack..."
    "$SCRIPT_DIR/cleanup_test_stack.sh"
fi

# Print summary
echo ""
echo "=============================="
if [ "$TEST_FAILED" = true ]; then
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    if [ "$KEEP_STACK" = true ] && [ -f "$TEST_CONFIG_FILE" ]; then
        echo ""
        echo "📌 Test stack preserved for debugging"
        echo "   To clean up later, run: ./scripts/cleanup_test_stack.sh"
    fi
    exit 0
fi
