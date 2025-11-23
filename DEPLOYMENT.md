# PromoTracker - Deployment Guide

This guide walks you through deploying the PromoTracker serverless infrastructure to AWS.

## Prerequisites

1. **AWS Account** - You need an AWS account with appropriate permissions
2. **AWS CLI** - Installed and configured with credentials
   ```bash
   aws configure
   ```
3. **Node.js & npm** - Required for AWS CDK (version 18.x or later)
   ```bash
   # Check if installed
   node --version
   npm --version

   # If not installed:
   # macOS: brew install node
   # Windows: Download from nodejs.org
   # Linux: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   ```

   **Important**: The Python CDK library requires Node.js runtime (via JSII). Even though Lambda functions are in Python, the CDK CLI is a Node.js tool.

4. **AWS CDK CLI** - Install globally via npm
   ```bash
   npm install -g aws-cdk
   cdk --version
   ```
5. **Python 3.12+** - For Lambda functions
   ```bash
   python3 --version
   ```

## API Keys Setup

Before deploying, you need to configure API keys in AWS Systems Manager Parameter Store. The Lambda functions will securely retrieve these at runtime.

### Required API Keys

1. **Firecrawl API Key** - Used by the Scraper Lambda for advanced web scraping
2. **OpenAI API Key** - Used by the Detector Lambda for promotion detection (optional for initial deployment)

### Where to Get API Keys

- **Firecrawl**: Sign up at [https://firecrawl.dev](https://firecrawl.dev) to get your API key
- **OpenAI**: Create an account at [https://platform.openai.com](https://platform.openai.com) and generate an API key

### Store API Keys in Parameter Store

Run these commands to securely store your API keys (replace placeholders with your actual keys):

```bash
# Store Firecrawl API key
aws ssm put-parameter \
    --name "/PromoTracker/FirecrawlApiKey" \
    --description "Firecrawl API key for web scraping" \
    --value "YOUR_FIRECRAWL_API_KEY_HERE" \
    --type "SecureString" \
    --region eu-west-2 \
    --overwrite

# Store OpenAI API key
aws ssm put-parameter \
    --name "/PromoTracker/OpenAIApiKey" \
    --description "OpenAI API key for promotion detection" \
    --value "YOUR_OPENAI_API_KEY_HERE" \
    --type "SecureString" \
    --region eu-west-2 \
    --overwrite
```

### Verify Parameters Were Created

```bash
aws ssm describe-parameters \
    --parameter-filters "Key=Name,Option=BeginsWith,Values=/PromoTracker/" \
    --region eu-west-2 \
    --query 'Parameters[*].[Name, Type, Description]' \
    --output table
```

You should see both parameters listed with type `SecureString`.

### Security Notes

- **SecureString encryption**: API keys are encrypted at rest using AWS KMS
- **IAM permissions**: Lambda functions have least-privilege access to only their required parameters
- **Cost**: Standard parameters in Parameter Store are **FREE** (no charges)
- **Region**: Parameters must be in the same region as your Lambda functions (eu-west-2)

## Infrastructure Overview

The CDK stack deploys:
- **4 DynamoDB Tables**: Websites, Promotions, Predictions, ScrapingMetrics
- **1 S3 Bucket**: HTML storage with lifecycle policies
- **4 Lambda Functions**: GetWebsites, Scraper, Detector, Predictor
- **1 Step Functions State Machine**: Orchestrates the scraping pipeline
- **1 EventBridge Rule**: Daily trigger at 09:00 UTC

## Deployment Steps

### Quick Start (Recommended)

Use the automated deployment script:

```bash
./scripts/deploy.sh
```

This script handles everything: installing Lambda dependencies, activating venv, and deploying.

### Manual Deployment

If you prefer manual control:

### 1. Install Lambda Layer Dependencies

```bash
cd lambdas/shared_layer
pip install -r requirements.txt -t python/ --upgrade
```

**Important**: This installs `requests`, `beautifulsoup4`, and other dependencies into the shared layer that all Lambda functions use.

### 2. Navigate to Infrastructure Directory

```bash
cd ../../infrastructure
```

### 3. Install CDK Dependencies

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Install Python CDK dependencies
pip install -r requirements.txt
```

### 4. Bootstrap CDK (First Time Only)

If this is your first time using CDK in this AWS account/region:

```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/eu-west-2
```

Replace `YOUR_ACCOUNT_ID` with your actual AWS account ID (found in [app.py](infrastructure/app.py:11)).

### 5. Review the Changes

```bash
cdk synth
```

This generates the CloudFormation template. Review it to understand what will be deployed.

### 6. Deploy the Stack

```bash
cdk deploy
```

You'll be asked to confirm security-related changes (IAM roles, policies). Review and approve by typing `y`.

**Expected deployment time**: 5-10 minutes

### 7. Save the Outputs

After deployment, CDK will output important resource names:

```
InfrastructureStack.WebsitesTableName = InfrastructureStack-WebsitesTable...
InfrastructureStack.PromotionsTableName = InfrastructureStack-PromotionsTable...
InfrastructureStack.PredictionsTableName = InfrastructureStack-PredictionsTable...
InfrastructureStack.MetricsTableName = InfrastructureStack-ScrapingMetricsTable...
InfrastructureStack.HtmlBucketName = infrastructurestack-htmlbucket...
InfrastructureStack.StateMachineArn = arn:aws:states:eu-west-2:...
```

**Save these values** - you'll need them for testing.

## Post-Deployment Setup

### 1. Verify API Keys

Before testing, ensure your API keys are configured in Parameter Store (see [API Keys Setup](#api-keys-setup) section above).

### 2. Seed Test Data

Populate the Websites table with test data:

```bash
cd ../scripts
python seed_test_data.py <WEBSITES_TABLE_NAME>
```

Replace `<WEBSITES_TABLE_NAME>` with the value from CDK outputs.

### 3. Test the Pipeline Manually

Trigger the Step Functions state machine:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --input '{"triggered_by":"manual","test":true}'
```

Replace `<STATE_MACHINE_ARN>` with the ARN from CDK outputs.

### 4. Monitor Execution

View the execution in the AWS Console:
1. Go to **Step Functions** → **State machines**
2. Find `PromoTrackerStateMachine`
3. Click on the latest execution
4. Watch the visual workflow

### 5. Verify Data

Check that data was written:

```bash
# Check promotions found
aws dynamodb scan --table-name <PROMOTIONS_TABLE_NAME> --limit 10

# Check predictions generated
aws dynamodb scan --table-name <PREDICTIONS_TABLE_NAME> --limit 10

# Check S3 for HTML files
aws s3 ls s3://<HTML_BUCKET_NAME>/html/ --recursive
```

## Cost Monitoring

Set up billing alerts:

```bash
# Create a billing alarm (requires CloudWatch)
aws cloudwatch put-metric-alarm \
  --alarm-name PromoTracker-CostAlert \
  --alarm-description "Alert when estimated charges exceed $2" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 2 \
  --comparison-operator GreaterThanThreshold
```

**Expected monthly cost**: $0.50 - $2.00 (staying within AWS Free Tier)

## Troubleshooting

### Issue: Lambda fails with API key errors

**Symptoms**: Scraper or Detector Lambda functions fail with errors like "Failed to load API key" or "Parameter not found"

**Solution**:
1. Verify API keys are stored in Parameter Store:
```bash
aws ssm get-parameter --name "/PromoTracker/FirecrawlApiKey" --region eu-west-2 --with-decryption
aws ssm get-parameter --name "/PromoTracker/OpenAIApiKey" --region eu-west-2 --with-decryption
```

2. Check Lambda IAM permissions include `ssm:GetParameter`:
```bash
# Check scraper function role
aws iam list-attached-role-policies --role-name InfrastructureStack-ScraperFunction*

# Check detector function role
aws iam list-attached-role-policies --role-name InfrastructureStack-DetectorFunction*
```

3. Ensure parameters are in the correct region (eu-west-2)

### Issue: Lambda deployment fails

**Solution**: Ensure Lambda directories have `handler.py` and `requirements.txt`:
```bash
ls -la ../lambdas/*/
```

### Issue: DynamoDB access denied

**Solution**: Check IAM permissions in the Lambda execution role:
```bash
aws iam get-role --role-name InfrastructureStack-GetWebsitesFunction...
```

### Issue: Step Functions execution fails

**Solution**: Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/InfrastructureStack-ScraperFunction --follow
```

### Issue: CDK synth fails

**Solution**: Ensure you're in the infrastructure directory and dependencies are installed:
```bash
cd infrastructure
source .venv/bin/activate
pip install -r requirements.txt
```

## Cleanup

To avoid ongoing charges, destroy the stack:

```bash
cd infrastructure
cdk destroy
```

**Note**: DynamoDB tables and S3 buckets with `RETAIN` policy will not be deleted. Delete them manually if needed:

```bash
aws dynamodb delete-table --table-name <WEBSITES_TABLE_NAME>
aws s3 rb s3://<HTML_BUCKET_NAME> --force
```

## Next Steps

1. **Set up API Gateway** - Add REST API for frontend access
2. **Implement LLM detection** - Upgrade detector with Claude API
3. **Add Prophet predictions** - Implement time series forecasting
4. **Build frontend** - Create React dashboard
5. **Set up CI/CD** - Automate deployments with GitHub Actions

## Architecture Diagram

```
┌─────────────────┐
│  EventBridge    │  Daily 09:00 UTC
│  Scheduler      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│   Step Functions State Machine          │
│  ┌────────────────────────────────────┐ │
│  │ 1. GetWebsites Lambda              │ │
│  │    ↓                               │ │
│  │ 2. Map (parallel, max 10)          │ │
│  │    ├─ Scraper Lambda               │ │
│  │    ├─ Detector Lambda              │ │
│  │    └─ Predictor Lambda             │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
         │
         ├─────────────────┐
         ▼                 ▼
    ┌──────────┐     ┌──────────┐
    │ DynamoDB │     │    S3    │
    │  Tables  │     │  Bucket  │
    └──────────┘     └──────────┘
```

## Support

For issues or questions:
- Check [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for system design
- Review [docs/PROJECT_ROADMAP.md](../docs/PROJECT_ROADMAP.md) for implementation plan
- Open an issue on GitHub
