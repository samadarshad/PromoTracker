"""
Shared pytest fixtures for PromoTracker tests
"""
import json
import os
from pathlib import Path
import pytest
import boto3
from moto import mock_aws


# Test data fixtures
@pytest.fixture
def sample_website():
    """Sample website data for testing"""
    return {
        "website_id": "test_website_1",
        "name": "Test Store",
        "url": "https://example.com/promotions",
        "enabled": "true",
        "scraping_frequency": "daily",
        "css_selectors": {
            "promotions_container": ".promotions"
        }
    }


@pytest.fixture
def sample_websites():
    """Multiple sample websites for testing"""
    return [
        {
            "website_id": "test_website_1",
            "name": "Test Store 1",
            "url": "https://example1.com/promotions",
            "enabled": "true"
        },
        {
            "website_id": "test_website_2",
            "name": "Test Store 2",
            "url": "https://example2.com/deals",
            "enabled": "true"
        },
        {
            "website_id": "test_website_3",
            "name": "Test Store 3",
            "url": "https://example3.com/sales",
            "enabled": "false"
        }
    ]


@pytest.fixture
def sample_promotion():
    """Sample promotion data"""
    return {
        "promotion_id": "promo_123",
        "website_id": "test_website_1",
        "title": "50% Off Summer Sale",
        "description": "Get 50% off all summer items",
        "discount_percentage": 50,
        "discount_code": "SUMMER50",
        "valid_until": "2024-07-31",
        "timestamp": "2024-07-01T10:00:00Z"
    }


@pytest.fixture
def sample_promotions():
    """Multiple sample promotions for testing"""
    return [
        {
            "promotion_id": "promo_1",
            "website_id": "test_website_1",
            "title": "20% Off",
            "discount_percentage": 20,
            "timestamp": "2024-01-15T10:00:00Z"
        },
        {
            "promotion_id": "promo_2",
            "website_id": "test_website_1",
            "title": "30% Off",
            "discount_percentage": 30,
            "timestamp": "2024-03-20T10:00:00Z"
        },
        {
            "promotion_id": "promo_3",
            "website_id": "test_website_1",
            "title": "25% Off",
            "discount_percentage": 25,
            "timestamp": "2024-05-10T10:00:00Z"
        }
    ]


# Environment variable fixtures
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for Lambda functions"""
    env_vars = {
        "WEBSITES_TABLE": "test-websites-table",
        "PROMOTIONS_TABLE": "test-promotions-table",
        "PREDICTIONS_TABLE": "test-predictions-table",
        "METRICS_TABLE": "test-metrics-table",
        "HTML_BUCKET": "test-html-bucket",
        "ENVIRONMENT": "test",
        "AWS_DEFAULT_REGION": "eu-west-2"
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# AWS service mocks
@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for moto"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-2")


@pytest.fixture
def dynamodb_mock(aws_credentials):
    """Mock DynamoDB service"""
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="eu-west-2")


@pytest.fixture
def s3_mock(aws_credentials):
    """Mock S3 service"""
    with mock_aws():
        yield boto3.client("s3", region_name="eu-west-2")


@pytest.fixture
def ssm_mock(aws_credentials):
    """Mock SSM Parameter Store"""
    with mock_aws():
        yield boto3.client("ssm", region_name="eu-west-2")


@pytest.fixture
def lambda_client_mock(aws_credentials):
    """Mock Lambda client for invocation tests"""
    with mock_aws():
        yield boto3.client("lambda", region_name="eu-west-2")


# Test infrastructure config
@pytest.fixture
def test_config():
    """Load test configuration from deployed test stack"""
    config_file = Path(__file__).parent / ".test-config.json"

    if not config_file.exists():
        pytest.skip("Test stack not deployed. Run ./scripts/deploy_test_stack.sh first")

    with open(config_file) as f:
        config_data = json.load(f)

    # Extract TestStack outputs
    if "TestStack" in config_data:
        return config_data["TestStack"]
    return config_data


@pytest.fixture
def lambda_client():
    """Real AWS Lambda client for integration tests"""
    return boto3.client("lambda", region_name="eu-west-2")


@pytest.fixture
def dynamodb_client():
    """Real AWS DynamoDB client for integration tests"""
    return boto3.client("dynamodb", region_name="eu-west-2")


@pytest.fixture
def s3_client():
    """Real AWS S3 client for integration tests"""
    return boto3.client("s3", region_name="eu-west-2")


@pytest.fixture
def stepfunctions_client():
    """Real AWS Step Functions client for e2e tests"""
    return boto3.client("stepfunctions", region_name="eu-west-2")


# Cleanup fixtures
@pytest.fixture
def cleanup_test_data(test_config, dynamodb_client, s3_client):
    """Clean up test data after integration tests"""
    yield

    # Cleanup logic runs after test
    if "TestPromotionsTableName" in test_config:
        table_name = test_config["TestPromotionsTableName"]
        # Note: Cleanup can be implemented here if needed
        # For now, we rely on stack cleanup script
