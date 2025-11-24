#!/bin/bash
# Deploy temporary test stack for serverless application testing
# This script deploys the test CDK stack and captures outputs for use in tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
TEST_CONFIG_FILE="$PROJECT_ROOT/tests/.test-config.json"

echo "🚀 Deploying Test Stack for PromoTracker"
echo "=========================================="
echo ""

# Change to infrastructure directory
cd "$INFRASTRUCTURE_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   cd infrastructure && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies if needed
echo "📦 Installing CDK dependencies..."
pip install -q -r requirements.txt

# Build Lambda layers if needed
echo "🔨 Building Lambda layers..."
cd "$PROJECT_ROOT"

# Build dependencies layer
if [ ! -d "layers/dependencies/python" ]; then
    echo "   Building dependencies layer..."
    mkdir -p layers/dependencies/python
    pip install -r lambdas/shared_layer/requirements.txt -t layers/dependencies/python/ --upgrade -q
fi

# Build shared code layer
if [ ! -d "layers/shared_code/python" ]; then
    echo "   Building shared code layer..."
    mkdir -p layers/shared_code/python
    cp -r lambdas/shared_layer/*.py layers/shared_code/python/
fi

cd "$INFRASTRUCTURE_DIR"

# Bootstrap CDK if needed (first-time setup)
echo "🔧 Checking CDK bootstrap status..."
cdk bootstrap aws://034894101750/eu-west-2 2>/dev/null || echo "   Already bootstrapped"

# Synthesize the test stack
echo "🏗️  Synthesizing test stack..."
cdk synth TestStack

# Deploy the test stack
echo "🚀 Deploying test stack to AWS..."
echo "   This may take 5-10 minutes..."
echo ""

cdk deploy TestStack --require-approval never --outputs-file "$TEST_CONFIG_FILE"

# Check if deployment succeeded
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Test stack deployed successfully!"
    echo ""
    echo "📋 Stack outputs saved to: $TEST_CONFIG_FILE"
    echo ""

    # Display key outputs
    echo "Key Resources:"
    echo "-------------"
    cat "$TEST_CONFIG_FILE" | grep -E "(TableName|BucketName|FunctionName|FunctionArn|StateMachineArn)" | sed 's/^/  /'
    echo ""

    # Create test data directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/tests"

    echo "Next steps:"
    echo "----------"
    echo "1. Store test API keys in Parameter Store:"
    echo "   aws ssm put-parameter --name \"/PromoTracker/Test/FirecrawlApiKey\" --value \"YOUR_KEY\" --type \"SecureString\" --region eu-west-2 --overwrite"
    echo "   aws ssm put-parameter --name \"/PromoTracker/Test/OpenAIApiKey\" --value \"YOUR_KEY\" --type \"SecureString\" --region eu-west-2 --overwrite"
    echo ""
    echo "2. Seed test data (optional):"
    echo "   python scripts/seed_test_data.py <TEST_WEBSITES_TABLE_NAME>"
    echo ""
    echo "3. Run tests:"
    echo "   ./scripts/run_tests.sh"
    echo ""
    echo "4. Clean up when done:"
    echo "   ./scripts/cleanup_test_stack.sh"
    echo ""
else
    echo ""
    echo "❌ Test stack deployment failed!"
    echo "   Check the error messages above for details."
    exit 1
fi
