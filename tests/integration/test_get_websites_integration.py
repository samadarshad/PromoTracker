"""
Integration tests for GetWebsites Lambda function
Tests against deployed test stack
"""
import pytest
import json
import boto3


@pytest.mark.integration
class TestGetWebsitesIntegration:
    """Integration tests for GetWebsites Lambda"""

    def test_get_websites_lambda_invocation(self, test_config, lambda_client):
        """Test invoking GetWebsites Lambda against test DynamoDB"""
        # Skip if test stack not deployed
        if not test_config:
            pytest.skip("Test stack not deployed")

        # Get Lambda function name from test config
        function_name = test_config.get("TestGetWebsitesFunctionName")
        if not function_name:
            pytest.skip("GetWebsites function not found in test config")

        # Invoke Lambda
        payload = {}

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

        # Verify response structure (Lambda returns direct JSON)
        assert 'statusCode' in response_payload
        assert response_payload['statusCode'] == 200
        assert 'websites' in response_payload
        assert isinstance(response_payload['websites'], list)

    def test_get_websites_returns_only_enabled(self, test_config, lambda_client, dynamodb_client, sample_websites):
        """Test that GetWebsites only returns enabled websites"""
        # Skip if test stack not deployed
        if not test_config:
            pytest.skip("Test stack not deployed")

        # Get table name from config
        table_name = test_config.get("TestWebsitesTableName")
        if not table_name:
            pytest.skip("Websites table not found in test config")

        # Seed test data
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        table = dynamodb.Table(table_name)

        # Insert test websites
        for website in sample_websites:
            table.put_item(Item=website)

        # Get Lambda function name
        function_name = test_config.get("TestGetWebsitesFunctionName")

        # Invoke Lambda
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({})
        )

        response_payload = json.loads(response['Payload'].read())

        # Check for Lambda errors
        if 'errorMessage' in response_payload:
            pytest.fail(f"Lambda execution failed: {response_payload.get('errorMessage')}")

        # Should only return enabled websites (2 out of 3)
        websites_returned = response_payload['websites']
        assert len(websites_returned) >= 2  # At least our 2 enabled test websites

        # Verify all returned websites are enabled
        for website in websites_returned:
            assert website['enabled'] == 'true'

        # Cleanup - delete test data
        for website in sample_websites:
            table.delete_item(Key={'website_id': website['website_id']})
