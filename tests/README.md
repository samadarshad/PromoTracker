# PromoTracker Testing Guide

This guide explains how to test the PromoTracker serverless application using AWS best practices for cloud-based testing.

## Overview

PromoTracker uses a comprehensive testing strategy that follows the AWS testing pyramid:

- **70% Unit Tests** - Fast, isolated tests with mocked dependencies
- **20% Integration Tests** - Test Lambda functions against real AWS services
- **10% End-to-End Tests** - Test complete workflow through Step Functions

## Testing Architecture

### Test Stack
Tests run against a temporary CDK stack (`TestStack`) that mirrors production but with:
- Aggressive cleanup policies (auto-delete resources)
- Shorter data retention (1 day)
- Tagged with `Environment: test` for easy identification
- Separate Parameter Store keys (`/PromoTracker/Test/*`)

### API Mocking
External APIs (Firecrawl, OpenAI) are mocked to:
- Avoid API costs during testing
- Ensure deterministic test results
- Prevent rate limit issues
- Enable fast test execution

## Quick Start

### 1. Install Test Dependencies

```bash
# Create and activate virtual environment for tests
python3 -m venv tests/.venv
source tests/.venv/bin/activate

# Install dependencies
pip install -r tests/requirements.txt
```

### 2. Run Unit Tests Only (No AWS Stack Needed)

```bash
# Fast tests with mocked dependencies
./scripts/run_tests.sh --unit-only
```

### 3. Run All Tests (Requires Test Stack)

```bash
# Deploy test stack, run all tests, and clean up
./scripts/run_tests.sh --all --cleanup
```

## Test Commands

### Deploy Test Stack

```bash
# Deploy temporary test infrastructure
./scripts/deploy_test_stack.sh
```

This will:
- Deploy TestStack to AWS
- Create test DynamoDB tables, S3 bucket, Lambda functions
- Save configuration to `tests/.test-config.json`
- Output resource names for manual testing

### Run Tests

```bash
# Run only unit tests (default)
./scripts/run_tests.sh

# Run unit + integration tests
./scripts/run_tests.sh --integration

# Run all test types
./scripts/run_tests.sh --all

# Keep test stack after running (for debugging)
./scripts/run_tests.sh --all --keep-stack

# Use existing stack without redeploying
./scripts/run_tests.sh --no-deploy --all
```

### Clean Up Test Stack

```bash
# Destroy test stack and remove test data
./scripts/cleanup_test_stack.sh
```

## Test Types

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual Lambda handlers in isolation

**Characteristics**:
- Run in milliseconds
- All dependencies mocked (boto3, HTTP requests)
- No AWS credentials needed
- Can run locally without internet

**Example**:
```bash
pytest tests/unit/test_scraper_unit.py -v
```

**What's Tested**:
- Lambda handler logic
- Error handling
- Data transformations
- Business logic calculations

### Integration Tests (`tests/integration/`)

**Purpose**: Test Lambda functions against real AWS services

**Characteristics**:
- Run against deployed TestStack
- Real DynamoDB, S3, Lambda services
- External APIs still mocked (Firecrawl, OpenAI)
- Takes seconds to minutes

**Example**:
```bash
pytest tests/integration/ -v -m integration
```

**What's Tested**:
- Lambda invocation
- IAM permissions
- DynamoDB reads/writes
- S3 uploads/downloads
- Service integrations

### End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete workflow through Step Functions

**Characteristics**:
- Tests full pipeline
- Real AWS orchestration
- Verifies data flow
- Takes minutes

**Example**:
```bash
pytest tests/e2e/ -v -m e2e
```

**What's Tested**:
- Step Functions state machine
- Lambda orchestration
- Error handling and retries
- Complete data pipeline

## Test Configuration

### pytest.ini

Defines test markers and coverage settings:

```ini
[pytest]
markers =
    unit: Unit tests (fast, with mocked dependencies)
    integration: Integration tests (requires deployed test stack)
    e2e: End-to-end tests (full workflow testing)
```

### Test Fixtures (`conftest.py`)

Shared fixtures for all tests:
- `sample_website`: Mock website data
- `mock_env_vars`: Lambda environment variables
- `dynamodb_mock`: Mocked DynamoDB service
- `test_config`: Load deployed test stack configuration
- `lambda_client`: Real AWS Lambda client

## API Mocking

### Firecrawl API Mocks (`tests/mocks/firecrawl_mock.py`)

Available scenarios:
- `success`: Successful scrape with promotions
- `no_promotions`: Successful scrape, no promotions found
- `rate_limit`: 429 rate limit error
- `api_error`: 500 internal error
- `invalid_url`: Invalid URL error
- `timeout`: Request timeout

Usage in tests:
```python
import responses
from tests.mocks.firecrawl_mock import get_mock_response

@responses.activate
def test_scraper():
    responses.add(
        responses.POST,
        'https://api.firecrawl.dev/v2/scrape',
        json=get_mock_response("success"),
        status=200
    )
    # Test code here
```

### OpenAI API Mocks (`tests/mocks/openai_mock.py`)

Available scenarios:
- `promotions_found`: Multiple promotions detected
- `no_promotions`: No promotions in content
- `single_promotion`: One promotion found
- `malformed`: Invalid JSON response
- `api_error`: Server error
- `rate_limit`: Rate limit exceeded
- `auth_error`: Invalid API key

## Debugging Failed Tests

### Keep Test Stack for Investigation

```bash
./scripts/run_tests.sh --all --keep-stack
```

Then manually inspect resources:
```bash
# View DynamoDB data
aws dynamodb scan --table-name <TestTableName> --region eu-west-2

# Check S3 contents
aws s3 ls s3://<TestBucketName>/ --recursive

# View Lambda logs
aws logs tail /aws/lambda/TestStack-TestScraperFunction --follow
```

### Run Specific Test

```bash
# Run single test file
pytest tests/unit/test_scraper_unit.py -v

# Run specific test function
pytest tests/unit/test_scraper_unit.py::TestScraperUnit::test_scrape_success -v

# Run with verbose output
pytest tests/unit/test_scraper_unit.py -vv -s
```

### Check Test Coverage

```bash
# Generate coverage report
pytest tests/ --cov=lambdas --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## CI/CD Integration (Future)

The testing framework is designed for GitHub Actions integration:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
      - name: Run tests
        run: ./scripts/run_tests.sh --all --cleanup
```

## Cost Considerations

### Test Stack Costs

- **DynamoDB**: Pay-per-request, ~$0.25/million requests
- **Lambda**: Free tier covers most testing, ~$0.20/million requests
- **S3**: Negligible for test data, ~$0.023/GB
- **Step Functions**: ~$0.025/1000 state transitions

**Estimated cost**: $0.50 - $2.00 per full test run

### Cost Optimization Tips

1. Run unit tests frequently (free, no AWS resources)
2. Run integration tests on commits (minimal cost)
3. Run e2e tests before deployment (small cost)
4. Clean up test stacks promptly (auto-delete after 1 day)

## Troubleshooting

### Test stack deployment fails

**Solution**: Check CDK bootstrap status and IAM permissions
```bash
cdk bootstrap aws://034894101750/eu-west-2
```

### Integration tests skipped

**Cause**: Test stack not deployed

**Solution**:
```bash
./scripts/deploy_test_stack.sh
```

### Lambda fails with Parameter Store errors

**Cause**: Test API keys not configured

**Solution**:
```bash
aws ssm put-parameter \
  --name "/PromoTracker/Test/FirecrawlApiKey" \
  --value "YOUR_KEY" \
  --type "SecureString" \
  --region eu-west-2 \
  --overwrite
```

### Tests pass locally but fail in CI

**Cause**: AWS credentials not configured

**Solution**: Configure AWS credentials in CI environment

## Best Practices

1. **Run unit tests frequently** - They're fast and catch bugs early
2. **Mock external APIs** - Prevents rate limits and API costs
3. **Clean up test data** - Use fixtures with cleanup logic
4. **Tag test resources** - All test resources tagged with `Environment: test`
5. **Use temporary stacks** - Never test against production
6. **Verify IAM permissions** - Integration tests validate actual permissions
7. **Test error paths** - Include tests for failures and edge cases
8. **Keep tests isolated** - Each test should be independent

## Additional Resources

- [AWS Prescriptive Guidance - Serverless Testing](https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-application-testing/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Moto - AWS Service Mocking](https://github.com/getmoto/moto)
- [Project Architecture](../docs/ARCHITECTURE.md)
- [Deployment Guide](../DEPLOYMENT.md)
