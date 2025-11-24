#!/bin/bash
# Clean up test stack and all associated resources
# This script destroys the test CDK stack and removes test data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
TEST_CONFIG_FILE="$PROJECT_ROOT/tests/.test-config.json"

echo "🧹 Cleaning Up Test Stack for PromoTracker"
echo "=========================================="
echo ""

# Check if test config exists
if [ ! -f "$TEST_CONFIG_FILE" ]; then
    echo "⚠️  No test configuration found at: $TEST_CONFIG_FILE"
    echo "   Test stack may not be deployed or was already cleaned up."
    read -p "   Continue with cleanup anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cleanup cancelled."
        exit 1
    fi
fi

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

# Confirm destruction
echo "⚠️  WARNING: This will destroy the test stack and all data!"
echo ""
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled."
    exit 1
fi

echo ""

# Extract bucket name from config for manual emptying (if needed)
if [ -f "$TEST_CONFIG_FILE" ]; then
    BUCKET_NAME=$(cat "$TEST_CONFIG_FILE" | grep -o '"TestHtmlBucketName": "[^"]*"' | cut -d'"' -f4)

    if [ -n "$BUCKET_NAME" ]; then
        echo "🗑️  Emptying S3 bucket: $BUCKET_NAME..."
        aws s3 rm "s3://$BUCKET_NAME" --recursive --region eu-west-2 2>/dev/null || echo "   Bucket already empty or doesn't exist"
    fi
fi

# Destroy the test stack
echo "🔥 Destroying test stack..."
echo ""

cdk destroy TestStack --force

# Check if destruction succeeded
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Test stack destroyed successfully!"
    echo ""

    # Remove test config file
    if [ -f "$TEST_CONFIG_FILE" ]; then
        echo "🗑️  Removing test configuration file..."
        rm "$TEST_CONFIG_FILE"
    fi

    # Optionally clean up test Parameter Store parameters
    echo ""
    read -p "Remove test API keys from Parameter Store? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔑 Removing test Parameter Store parameters..."
        aws ssm delete-parameter --name "/PromoTracker/Test/FirecrawlApiKey" --region eu-west-2 2>/dev/null || echo "   FirecrawlApiKey not found or already deleted"
        aws ssm delete-parameter --name "/PromoTracker/Test/OpenAIApiKey" --region eu-west-2 2>/dev/null || echo "   OpenAIApiKey not found or already deleted"
    fi

    echo ""
    echo "✨ Cleanup complete!"
    echo ""
else
    echo ""
    echo "❌ Test stack destruction failed!"
    echo "   Check the error messages above for details."
    echo ""
    echo "Manual cleanup steps:"
    echo "1. Empty S3 bucket: aws s3 rm s3://BUCKET_NAME --recursive --region eu-west-2"
    echo "2. Delete stack: aws cloudformation delete-stack --stack-name TestStack --region eu-west-2"
    exit 1
fi
