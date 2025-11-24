"""
Integration tests for Scraper Lambda function
Tests against deployed test stack with mocked external APIs
"""
import pytest
import json
import sys
from pathlib import Path
import boto3
import responses

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.mocks.firecrawl_mock import get_mock_response


@pytest.mark.integration
class TestScraperIntegration:
    """Integration tests for scraper Lambda"""

    @responses.activate
    def test_scraper_lambda_invocation_success(self, test_config, lambda_client, sample_website):
        """Test invoking scraper Lambda with mocked Firecrawl API"""
        # Skip if test stack not deployed
        if not test_config:
            pytest.skip("Test stack not deployed")

        # Mock Firecrawl API
        responses.add(
            responses.POST,
            'https://api.firecrawl.dev/v2/scrape',
            json=get_mock_response("success"),
            status=200
        )

        # Get Lambda function name from test config
        function_name = test_config.get("TestScraperFunctionName")
        if not function_name:
            pytest.skip("Scraper function not found in test config")

        # Invoke Lambda
        payload = {"website": sample_website}

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Parse response
        response_payload = json.loads(response['Payload'].read())

        assert response['StatusCode'] == 200

        # Check if Lambda execution had an error
        if 'errorMessage' in response_payload:
            pytest.fail(f"Lambda execution failed: {response_payload.get('errorMessage')}\n{response_payload.get('stackTrace', '')}")

        # Lambda returns direct JSON
        assert 'statusCode' in response_payload
        assert response_payload['statusCode'] == 200
        assert response_payload.get('success') is True or 'error' not in response_payload

    def test_scraper_stores_data_in_s3(self, test_config, s3_client, sample_website):
        """Test that scraper stores scraped content in S3"""
        pytest.skip("Requires mocking Firecrawl API in Lambda environment")
        # This test would require more complex setup to mock APIs
        # within the Lambda execution environment

    @responses.activate
    def test_scraper_saves_metrics_to_dynamodb(self, test_config, dynamodb_client, sample_website):
        """Test that scraper saves metrics to DynamoDB"""
        pytest.skip("Requires mocking Firecrawl API in Lambda environment")
        # This test would require checking DynamoDB after Lambda execution
