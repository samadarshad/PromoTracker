"""
Lambda function to get all enabled websites from DynamoDB.
"""
import json
from dynamo_helper import DynamoDBHelper
from logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    Lambda handler to retrieve all enabled websites.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Dict with list of enabled websites
    """
    logger.info("Starting get_websites lambda", extra={'event': event})

    try:
        db_helper = DynamoDBHelper()
        websites = db_helper.get_enabled_websites()

        logger.info(f"Retrieved {len(websites)} enabled websites")

        return {
            'statusCode': 200,
            'websites': websites
        }

    except Exception as e:
        logger.error(f"Error getting websites: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
