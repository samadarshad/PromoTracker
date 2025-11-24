"""
Lambda function to scrape website content.
Uses only Firecrawl API with markdown output for cost-efficient LLM processing.
"""
import json
import os
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
import boto3
import requests
from shared.dynamo_helper import DynamoDBHelper
from shared.s3_helper import S3Helper
from shared.logger import get_logger

logger = get_logger(__name__)

# Cache for API key (loaded once per Lambda container)
_firecrawl_api_key: Optional[str] = None


def get_firecrawl_api_key() -> str:
    """
    Get Firecrawl API key from AWS Parameter Store (cached).

    Returns:
        API key string
    """
    global _firecrawl_api_key

    if _firecrawl_api_key is not None:
        return _firecrawl_api_key

    try:
        ssm_client = boto3.client('ssm', region_name='eu-west-2')
        response = ssm_client.get_parameter(
            Name='/PromoTracker/FirecrawlApiKey',
            WithDecryption=True  # Decrypt SecureString
        )
        _firecrawl_api_key = response['Parameter']['Value']
        logger.info("Firecrawl API key loaded from Parameter Store")
        return _firecrawl_api_key
    except Exception as e:
        logger.error(f"Failed to load Firecrawl API key: {str(e)}")
        raise


def scrape_with_firecrawl(url: str) -> Tuple[str, float]:
    """
    Scrape website using Firecrawl API v2 with markdown output.

    Args:
        url: URL to scrape

    Returns:
        Tuple of (markdown content, cost in USD)

    Raises:
        Exception if Firecrawl scraping fails
    """
    api_key = get_firecrawl_api_key()

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Firecrawl v2 API payload - markdown only for LLM cost efficiency
    payload = {
        'url': url,
        'formats': ['markdown'],  # Only request markdown, not HTML
        'onlyMainContent': True,  # Extract main content, skip nav/footer
        'includeTags': [],  # No specific tags filter
        'excludeTags': ['nav', 'footer', 'script', 'style'],  # Skip these
        'waitFor': 0  # No wait time for JS rendering
    }

    # Get Firecrawl API URL from environment (allows for mock server in tests)
    firecrawl_api_url = os.getenv('FIRECRAWL_API_URL', 'https://api.firecrawl.dev/v2/scrape')

    try:
        logger.info(f"Attempting Firecrawl v2 scrape for {url} via {firecrawl_api_url}")
        response = requests.post(
            firecrawl_api_url,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            error_msg = data.get('error', 'Unknown error')
            raise Exception(f"Firecrawl API returned success=false: {error_msg}")

        # Extract markdown content from v2 response structure
        result_data = data.get('data', {})
        content = result_data.get('markdown', '')

        if not content:
            raise Exception("Firecrawl returned empty markdown content")

        # Calculate cost
        # v2 pricing: typically 1 credit per scrape = ~$0.0006
        credits_used = data.get('creditsUsed', 1)
        cost = credits_used * 0.0006

        logger.info(f"Firecrawl v2 scrape successful. Credits: {credits_used}, Cost: ${cost:.4f}")
        logger.info(f"Markdown content length: {len(content)} chars")

        return content, cost

    except requests.exceptions.RequestException as e:
        logger.error(f"Firecrawl API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"API error details: {error_detail}")
            except:
                logger.error(f"API response text: {e.response.text}")
        raise Exception(f"Firecrawl v2 scraping failed: {str(e)}")


def lambda_handler(event, context):
    """
    Lambda handler to scrape website content using Firecrawl with markdown output.

    Args:
        event: Lambda event containing website data
        context: Lambda context

    Returns:
        Dict with scraping result
    """
    logger.info("Starting scraper lambda", extra={'event': event})

    try:
        website = event.get('website', {})
        website_id = website.get('website_id')
        url = website.get('url')

        if not website_id or not url:
            raise ValueError("Missing required fields: website_id or url")

        start_time = time.time()
        scrape_cost = Decimal('0')

        # Use Firecrawl with markdown output
        logger.info(f"Scraping {url} with Firecrawl (markdown output)")
        try:
            markdown_content, cost = scrape_with_firecrawl(url)
            scrape_cost = Decimal(str(cost))
            logger.info(f"Firecrawl scrape successful. Cost: ${cost:.4f}")
        except Exception as firecrawl_error:
            logger.error(f"Firecrawl scraping failed: {str(firecrawl_error)}")
            raise Exception(f"Firecrawl scraping failed: {firecrawl_error}")

        scrape_duration = time.time() - start_time

        # Save to S3
        s3_helper = S3Helper()
        timestamp = datetime.utcnow().isoformat()
        s3_key = s3_helper.upload_markdown(website_id, markdown_content, timestamp)

        # Save metrics
        db_helper = DynamoDBHelper()
        metric_data = {
            'metric_id': f"{website_id}_{timestamp}",
            'timestamp': timestamp,
            'website_id': website_id,
            'scrape_duration': Decimal(str(scrape_duration)),  # Convert float to Decimal
            'content_length': len(markdown_content),
            'success': True,
            'method': 'firecrawl_markdown',  # Track that we're using Firecrawl with markdown
            'cost': scrape_cost,  # Track Firecrawl costs
            'ttl': int(time.time()) + (90 * 24 * 60 * 60)  # 90 days TTL
        }
        db_helper.save_metric(metric_data)

        logger.info(f"Successfully scraped {url} in {scrape_duration:.2f}s")

        return {
            'statusCode': 200,
            'website_id': website_id,
            'website': website,  # Preserve website data
            'scrape_result': {
                's3_key': s3_key,
                'timestamp': timestamp,
                'content_length': len(markdown_content),
                'scrape_duration': scrape_duration,
                'method': 'firecrawl_markdown',
                'cost': float(scrape_cost)  # Convert Decimal to float for JSON
            }
        }

    except Exception as e:
        logger.error(f"Error scraping website: {str(e)}")

        # Save failure metric
        try:
            db_helper = DynamoDBHelper()
            timestamp = datetime.utcnow().isoformat()
            metric_data = {
                'metric_id': f"{website_id if 'website_id' in locals() else 'unknown'}_{timestamp}",
                'timestamp': timestamp,
                'website_id': website_id if 'website_id' in locals() else 'unknown',
                'success': False,
                'error': str(e),
                'ttl': int(time.time()) + (90 * 24 * 60 * 60)
            }
            db_helper.save_metric(metric_data)
        except:
            pass

        return {
            'statusCode': 500,
            'error': str(e),
            'website_id': website_id if 'website_id' in locals() else 'unknown',
            'website': website if 'website' in locals() else {}
        }
