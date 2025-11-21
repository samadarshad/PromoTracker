"""
Lambda function to scrape website content.
Implements Tier 1 (basic HTTP) scraping with fallback support.
"""
import json
import random
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import requests
from urllib.robotparser import RobotFileParser
from dynamo_helper import DynamoDBHelper
from s3_helper import S3Helper
from logger import get_logger
from constants import USER_AGENTS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF

logger = get_logger(__name__)


def check_robots_txt(url: str) -> bool:
    """
    Check if scraping is allowed by robots.txt.

    Args:
        url: Website URL

    Returns:
        True if allowed, False otherwise
    """
    try:
        from urllib.parse import urljoin, urlparse
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        return rp.can_fetch("*", url)
    except Exception as e:
        logger.warning(f"Could not check robots.txt: {str(e)}")
        return True


def scrape_with_retry(url: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Scrape website with exponential backoff retry logic.

    Args:
        url: URL to scrape
        max_retries: Maximum number of retries

    Returns:
        HTML content as string

    Raises:
        Exception if all retries fail
    """
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            logger.warning(f"Scrape attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                sleep_time = RETRY_BACKOFF ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                raise Exception(f"Failed to scrape after {max_retries} attempts: {str(e)}")


def lambda_handler(event, context):
    """
    Lambda handler to scrape website content.

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

        # Check robots.txt
        if not check_robots_txt(url):
            logger.warning(f"Scraping not allowed by robots.txt for {url}")
            return {
                'statusCode': 403,
                'error': 'Scraping not allowed by robots.txt',
                'website_id': website_id,
                'website': website  # Preserve website data for downstream tasks
            }

        # Scrape the website
        start_time = time.time()
        html_content = scrape_with_retry(url)
        scrape_duration = time.time() - start_time

        # Save to S3
        s3_helper = S3Helper()
        timestamp = datetime.utcnow().isoformat()
        s3_key = s3_helper.upload_html(website_id, html_content, timestamp)

        # Save metrics
        db_helper = DynamoDBHelper()
        metric_data = {
            'metric_id': f"{website_id}_{timestamp}",
            'timestamp': timestamp,
            'website_id': website_id,
            'scrape_duration': Decimal(str(scrape_duration)),  # Convert float to Decimal
            'content_length': len(html_content),
            'success': True,
            'method': 'basic_http',
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
                'content_length': len(html_content),
                'scrape_duration': scrape_duration
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
