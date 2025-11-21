#!/bin/bash
# Deployment script for PromoTracker infrastructure

set -e  # Exit on error

echo "🚀 PromoTracker Deployment Script"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project directory: $PROJECT_DIR"
echo ""

# Step 1: Install Lambda layer dependencies
echo "📦 Step 1: Installing Lambda layer dependencies..."
cd "$PROJECT_DIR/lambdas/shared_layer"

if [ -f "requirements.txt" ]; then
    echo "  Installing to shared_layer/python/..."
    pip install -r requirements.txt -t python/ --upgrade --quiet
    echo -e "  ${GREEN}✓${NC} Dependencies installed"
else
    echo -e "  ${YELLOW}⚠${NC} No requirements.txt found, skipping"
fi
echo ""

# Step 2: Navigate to infrastructure directory
echo "📁 Step 2: Navigating to infrastructure directory..."
cd "$PROJECT_DIR/infrastructure"
echo -e "  ${GREEN}✓${NC} In infrastructure directory"
echo ""

# Step 3: Activate virtual environment
echo "🐍 Step 3: Activating virtual environment..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "  ${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "  ${RED}✗${NC} Virtual environment not found!"
    echo "  Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
echo ""

# Step 4: Check if cdk is available
echo "🔍 Step 4: Checking CDK CLI..."
if ! command -v cdk &> /dev/null; then
    echo -e "  ${RED}✗${NC} CDK CLI not found!"
    echo "  Install with: npm install -g aws-cdk"
    echo ""
    echo "  Note: You need Node.js and npm installed first."
    exit 1
fi

CDK_VERSION=$(cdk --version)
echo -e "  ${GREEN}✓${NC} CDK CLI found: $CDK_VERSION"
echo ""

# Step 5: Synthesize CloudFormation template
echo "🔨 Step 5: Synthesizing CDK stack..."
if cdk synth > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Stack synthesized successfully"
else
    echo -e "  ${RED}✗${NC} Failed to synthesize stack"
    echo "  Run 'cdk synth' manually to see errors"
    exit 1
fi
echo ""

# Step 6: Show diff (if stack already exists)
echo "📊 Step 6: Checking for changes..."
if cdk diff 2>&1 | grep -q "Stack InfrastructureStack"; then
    echo "  Stack changes detected. Run 'cdk diff' to see details."
else
    echo "  First deployment or no changes."
fi
echo ""

# Step 7: Deploy
echo "🚀 Step 7: Deploying to AWS..."
echo ""
echo "This will:"
echo "  - Create/update 4 DynamoDB tables"
echo "  - Create/update 1 S3 bucket"
echo "  - Deploy 4 Lambda functions with shared layer"
echo "  - Create Step Functions state machine"
echo "  - Set up EventBridge scheduler"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Deploying..."
    echo ""

    if cdk deploy --require-approval never; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✓ Deployment successful!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Note the output values (table names, bucket name, etc.)"
        echo "  2. Seed test data: python scripts/seed_test_data.py <WEBSITES_TABLE_NAME>"
        echo "  3. Test the pipeline via AWS Console → Step Functions"
        echo ""
    else
        echo ""
        echo -e "${RED}✗ Deployment failed${NC}"
        echo "Check the error messages above for details."
        exit 1
    fi
else
    echo ""
    echo "Deployment cancelled."
    exit 0
fi
