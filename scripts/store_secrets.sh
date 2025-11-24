#!/bin/bash
# Script to store API keys in AWS Systems Manager Parameter Store

set -e

echo "🔐 Storing API Keys in AWS Parameter Store"
echo "=========================================="
echo ""

# Firecrawl API Key
echo "Storing Firecrawl API key..."
aws ssm put-parameter \
    --name "/PromoTracker/FirecrawlApiKey" \
    --description "Firecrawl API key for web scraping" \
    --value "fc-2c337d83742e4e60b6d5588504b809f8" \
    --type "SecureString" \
    --region eu-west-2 \
    --overwrite \
    2>&1

echo ""
echo "✅ Parameters stored successfully!"
echo ""
echo "Parameter details:"
aws ssm describe-parameters \
    --parameter-filters "Key=Name,Values=/PromoTracker/FirecrawlApiKey" \
    --region eu-west-2 \
    --query 'Parameters[0].[Name, Type, Description]' \
    --output table

echo ""
echo "💰 Cost: FREE (Standard parameters in Parameter Store are free)"
echo ""
echo "Note: Lambda functions will need IAM permissions: ssm:GetParameter"
