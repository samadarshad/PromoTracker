"""
Lambda function to predict next promotion date.
Implements simple weighted average (placeholder for Prophet).
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from dynamo_helper import DynamoDBHelper
from logger import get_logger
from constants import MIN_DATA_POINTS_WEIGHTED, PREDICTION_DAYS_LOOKBACK

logger = get_logger(__name__)


def calculate_weighted_average(promotions: List[Dict[str, Any]]) -> int:
    """
    Calculate weighted average days between promotions.

    Args:
        promotions: List of promotion records

    Returns:
        Predicted days until next promotion
    """
    if len(promotions) < 2:
        return 30  # Default to 30 days if not enough data

    # Sort by timestamp
    sorted_promos = sorted(promotions, key=lambda x: x['timestamp'])

    # Calculate days between consecutive promotions
    intervals = []
    for i in range(1, len(sorted_promos)):
        prev_date = datetime.fromisoformat(sorted_promos[i-1]['timestamp'])
        curr_date = datetime.fromisoformat(sorted_promos[i]['timestamp'])
        days_diff = (curr_date - prev_date).days
        intervals.append(days_diff)

    if not intervals:
        return 30

    # Simple weighted average (more weight to recent intervals)
    weights = [2 ** i for i in range(len(intervals))]
    weighted_sum = sum(interval * weight for interval, weight in zip(intervals, weights))
    total_weight = sum(weights)

    return int(weighted_sum / total_weight)


def lambda_handler(event, context):
    """
    Lambda handler to predict next promotion.

    Args:
        event: Lambda event containing website and detection result
        context: Lambda context

    Returns:
        Dict with prediction result
    """
    logger.info("Starting predictor lambda", extra={'event': event})

    try:
        # Handle nested structure from Step Functions
        detector_output = event.get('detector_output', {}).get('Payload', {})
        website = detector_output.get('website', event.get('website', {}))
        detection_result = detector_output.get('detection_result', event.get('detection_result', {}))

        website_id = website.get('website_id')

        if not website_id:
            raise ValueError("Missing required field: website_id")

        # Get historical promotions
        db_helper = DynamoDBHelper()
        promotions = db_helper.get_website_promotions(website_id, limit=100)

        # Calculate prediction
        if len(promotions) < MIN_DATA_POINTS_WEIGHTED:
            # Not enough data - use calendar heuristic
            prediction_method = 'calendar_heuristic'
            days_until_next = 30
            confidence = 0.3
            logger.info(f"Using calendar heuristic for {website_id} - only {len(promotions)} data points")
        else:
            # Use weighted average
            prediction_method = 'weighted_average'
            days_until_next = calculate_weighted_average(promotions)
            confidence = 0.7
            logger.info(f"Using weighted average for {website_id} - {len(promotions)} data points")

        # Calculate predicted date
        predicted_date = (datetime.utcnow() + timedelta(days=days_until_next)).isoformat()
        prediction_timestamp = datetime.utcnow().isoformat()

        # Save prediction to DynamoDB
        prediction_data = {
            'website_id': website_id,
            'prediction_timestamp': prediction_timestamp,
            'predicted_date': predicted_date,
            'days_until_next': days_until_next,
            'prediction_method': prediction_method,
            'confidence': Decimal(str(confidence)),  # Convert float to Decimal
            'data_points_used': len(promotions),
            'is_latest': 'true'
        }

        db_helper.save_prediction(prediction_data)

        logger.info(f"Prediction saved for {website_id}: {days_until_next} days")

        return {
            'statusCode': 200,
            'website_id': website_id,
            'prediction': prediction_data
        }

    except Exception as e:
        logger.error(f"Error predicting next promotion: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'website_id': website_id
        }
