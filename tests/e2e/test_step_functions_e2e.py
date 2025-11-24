"""
End-to-end tests for Step Functions workflow
Tests complete pipeline from website retrieval to prediction
"""
import pytest
import json
import time
import sys
from pathlib import Path
import boto3
import responses

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.mocks.firecrawl_mock import get_mock_response
from tests.mocks.openai_mock import get_mock_response as get_openai_mock


@pytest.mark.e2e
@pytest.mark.slow
class TestStepFunctionsE2E:
    """End-to-end tests for Step Functions state machine"""

    def test_complete_workflow_with_mocked_apis(self, test_config, stepfunctions_client, dynamodb_client, sample_websites):
        """Test complete Step Functions workflow with mocked external APIs"""
        pytest.skip("Requires complex setup to mock APIs in Lambda execution environment")
        # This test would require:
        # 1. Seeding test websites in DynamoDB
        # 2. Mocking Firecrawl and OpenAI APIs (challenging in Lambda environment)
        # 3. Triggering Step Functions execution
        # 4. Polling execution status
        # 5. Verifying data in DynamoDB tables

    def test_step_functions_execution_starts(self, test_config, stepfunctions_client):
        """Test that Step Functions state machine can be triggered"""
        # Skip if test stack not deployed
        if not test_config:
            pytest.skip("Test stack not deployed")

        # Get state machine ARN from test config
        state_machine_arn = test_config.get("TestStateMachineArn")
        if not state_machine_arn:
            pytest.skip("State machine not found in test config")

        # Start execution
        execution_name = f"test-execution-{int(time.time())}"

        response = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps({
                "triggered_by": "test",
                "test": True
            })
        )

        assert 'executionArn' in response
        execution_arn = response['executionArn']

        # Wait briefly for execution to start
        time.sleep(2)

        # Describe execution to verify it started
        execution_desc = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )

        assert execution_desc['status'] in ['RUNNING', 'SUCCEEDED', 'FAILED']

        # Note: Execution might fail due to missing test data or unmocked APIs
        # This test just verifies the state machine can be triggered

    def test_get_websites_step_executes(self, test_config, stepfunctions_client, dynamodb_client, sample_websites):
        """Test that GetWebsites step executes successfully"""
        # Skip if test stack not deployed
        if not test_config:
            pytest.skip("Test stack not deployed")

        # Get resources from config
        state_machine_arn = test_config.get("TestStateMachineArn")
        table_name = test_config.get("TestWebsitesTableName")

        if not state_machine_arn or not table_name:
            pytest.skip("Required resources not found in test config")

        # Seed test websites
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        table = dynamodb.Table(table_name)

        # Insert one enabled test website
        test_website = sample_websites[0]  # First website is enabled
        table.put_item(Item=test_website)

        try:
            # Start execution
            execution_name = f"test-get-websites-{int(time.time())}"

            response = stepfunctions_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps({
                    "triggered_by": "test"
                })
            )

            execution_arn = response['executionArn']

            # Wait for execution to progress
            max_wait = 30  # seconds
            wait_interval = 2
            waited = 0

            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval

                execution_desc = stepfunctions_client.describe_execution(
                    executionArn=execution_arn
                )

                status = execution_desc['status']

                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    break

            # Get execution history to verify GetWebsites step executed
            history = stepfunctions_client.get_execution_history(
                executionArn=execution_arn,
                maxResults=100
            )

            # Look for GetWebsites task in history
            get_websites_executed = False
            for event in history['events']:
                if event['type'] == 'TaskStateEntered':
                    if 'GetWebsites' in str(event):
                        get_websites_executed = True
                        break

            assert get_websites_executed, "GetWebsites step did not execute"

        finally:
            # Cleanup - delete test website
            table.delete_item(Key={'website_id': test_website['website_id']})

    def wait_for_execution(self, stepfunctions_client, execution_arn, timeout=60):
        """Helper method to wait for execution to complete"""
        waited = 0
        while waited < timeout:
            time.sleep(5)
            waited += 5

            execution = stepfunctions_client.describe_execution(
                executionArn=execution_arn
            )

            status = execution['status']

            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                return execution

        raise TimeoutError(f"Execution did not complete within {timeout} seconds")
