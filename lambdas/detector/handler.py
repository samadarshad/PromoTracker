"""
Lambda function to detect promotions from scraped HTML.
Implements Tier 1 (CSS selectors) with placeholder for Tier 2 (LLM).
"""
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from dynamo_helper import DynamoDBHelper
from s3_helper import S3Helper
from logger import get_logger

logger = get_logger(__name__)


def detect_with_css_selectors(html: str, selectors: list) -> Optional[Dict[str, Any]]:
    """
    Detect promotions using CSS selectors.

    Args:
        html: HTML content
        selectors: List of CSS selectors to try

    Returns:
        Dict with promotion details or None if not found
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')

        for selector in selectors:
            elements = soup.select(selector)

            if elements:
                promotion_text = ' '.join([elem.get_text(strip=True) for elem in elements])

                return {
                    'found': True,
                    'method': 'css_selector',
                    'selector': selector,
                    'text': promotion_text[:500],  # Limit text length
                    'confidence': 0.9
                }

        return None

    except Exception as e:
        logger.error(f"Error in CSS selector detection: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler to detect promotions.

    Args:
        event: Lambda event containing website and scrape result
        context: Lambda context

    Returns:
        Dict with detection result
    """
    logger.info("Starting detector lambda", extra={'event': event})

    try:
        # Handle nested structure from Step Functions
        scraper_output = event.get('scraper_output', {}).get('Payload', {})
        website = scraper_output.get('website', event.get('website', {}))
        scrape_result = scraper_output.get('scrape_result', event.get('scrape_result', {}))

        website_id = website.get('website_id')
        s3_key = scrape_result.get('s3_key')
        selectors = website.get('promotion_selectors', [])

        if not website_id or not s3_key:
            raise ValueError("Missing required fields: website_id or s3_key")

        # Download HTML from S3
        s3_helper = S3Helper()
        html_content = s3_helper.download_html(s3_key)

        # Try CSS selector detection
        detection_result = None

        if selectors:
            detection_result = detect_with_css_selectors(html_content, selectors)

        # If promotion found, save to DynamoDB
        if detection_result and detection_result.get('found'):
            db_helper = DynamoDBHelper()
            timestamp = datetime.utcnow().isoformat()

            promotion_data = {
                'promotion_id': str(uuid.uuid4()),
                'timestamp': timestamp,
                'website_id': website_id,
                'promotion_text': detection_result.get('text', ''),
                'detection_method': detection_result.get('method'),
                'confidence': Decimal(str(detection_result.get('confidence', 0))),  # Convert float to Decimal
                's3_key': s3_key,
                'is_active': True
            }

            db_helper.save_promotion(promotion_data)

            logger.info(f"Promotion detected for {website_id}")

            return {
                'statusCode': 200,
                'website_id': website_id,
                'website': website,  # Preserve website data
                'detection_result': {
                    'promotion_found': True,
                    'promotion_id': promotion_data['promotion_id'],
                    'promotion_text': promotion_data['promotion_text'],
                    'confidence': promotion_data['confidence']
                }
            }
        else:
            logger.info(f"No promotion detected for {website_id}")

            return {
                'statusCode': 200,
                'website_id': website_id,
                'website': website,  # Preserve website data
                'detection_result': {
                    'promotion_found': False
                }
            }

    except Exception as e:
        logger.error(f"Error detecting promotion: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'website_id': website_id if 'website_id' in locals() else 'unknown',
            'website': website if 'website' in locals() else {}
        }
