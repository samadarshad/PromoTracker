"""
Lambda function to scrape website content.
Implements Tier 1 (basic HTTP) scraping with Tier 2 (Firecrawl) fallback.
"""
import json
import os
import random
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
import boto3
import requests
from urllib.robotparser import RobotFileParser
from dynamo_helper import DynamoDBHelper
from s3_helper import S3Helper
from logger import get_logger
from constants import USER_AGENTS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF

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


def scrape_with_firecrawl(url: str) -> Tuple[str, float]:
    """
    Scrape website using Firecrawl API v2.

    Args:
        url: URL to scrape

    Returns:
        Tuple of (HTML/markdown content, cost in USD)

    Raises:
        Exception if Firecrawl scraping fails
    """
    api_key = get_firecrawl_api_key()

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Firecrawl v2 API payload
    payload = {
        'url': url,
        'formats': ['html', 'markdown'],
        'onlyMainContent': True,  # Extract main content, skip nav/footer
        'includeTags': [],  # No specific tags filter
        'excludeTags': ['nav', 'footer', 'script', 'style'],  # Skip these
        'waitFor': 0  # No wait time for JS rendering
    }

    try:
        logger.info(f"Attempting Firecrawl v2 scrape for {url}")
        response = requests.post(
            'https://api.firecrawl.dev/v2/scrape',
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            error_msg = data.get('error', 'Unknown error')
            raise Exception(f"Firecrawl API returned success=false: {error_msg}")

        # Extract content from v2 response structure
        result_data = data.get('data', {})

        # Prefer HTML, fallback to markdown, then raw text
        content = (
            result_data.get('html') or
            result_data.get('markdown') or
            result_data.get('rawHtml') or
            ''
        )

        if not content:
            raise Exception("Firecrawl returned empty content")

        # Calculate cost
        # v2 pricing: typically 1 credit per scrape = ~$0.0006
        credits_used = data.get('creditsUsed', 1)
        cost = credits_used * 0.0006

        logger.info(f"Firecrawl v2 scrape successful. Credits: {credits_used}, Cost: ${cost:.4f}")
        logger.info(f"Content length: {len(content)} chars")

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


def scrape_with_retry(url: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Scrape website with exponential backoff retry logic (Tier 1 - Basic HTTP).

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

        except requests.exceptions.Timeout as e:
            # For timeout errors, fail faster (only 1 retry) to use Firecrawl sooner
            logger.warning(f"Scrape attempt {attempt + 1} timed out: {str(e)}")

            if attempt < 1:  # Only retry once for timeouts
                sleep_time = RETRY_BACKOFF ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.info(f"Timeout after {attempt + 1} attempts, will fallback to Firecrawl")
                raise Exception(f"Read timeout after {attempt + 1} attempts: {str(e)}")

        except requests.exceptions.RequestException as e:
            # For other errors (403, 429, etc), use full retry count
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

        # Two-tier scraping strategy with robots.txt handling
        html_content = None
        scrape_method = None
        scrape_cost = Decimal('0')
        start_time = time.time()
        robots_blocked = not check_robots_txt(url)

        if robots_blocked:
            # robots.txt blocks us - skip Tier 1, use Firecrawl directly
            logger.warning(f"robots.txt blocks scraping for {url}, using Firecrawl (Tier 2)")
            try:
                html_content, cost = scrape_with_firecrawl(url)
                scrape_method = 'firecrawl_robots'
                scrape_cost = Decimal(str(cost))
                logger.info(f"Firecrawl scrape successful (robots.txt bypass). Cost: ${cost:.4f}")
            except Exception as firecrawl_error:
                logger.error(f"Firecrawl scraping failed: {str(firecrawl_error)}")
                raise Exception(f"Firecrawl failed for robots.txt blocked site: {firecrawl_error}")

        else:
            # robots.txt allows us - try Tier 1 first, fallback to Tier 2
            try:
                # Tier 1: Try basic HTTP scraping first
                logger.info(f"Attempting Tier 1 (basic HTTP) scrape for {url}")
                html_content = scrape_with_retry(url)
                scrape_method = 'basic_http'
                logger.info("Tier 1 scraping successful")

            except Exception as tier1_error:
                logger.warning(f"Tier 1 scraping failed: {str(tier1_error)}")

                try:
                    # Tier 2: Fallback to Firecrawl
                    logger.info(f"Falling back to Tier 2 (Firecrawl) for {url}")
                    html_content, cost = scrape_with_firecrawl(url)
                    scrape_method = 'firecrawl'
                    scrape_cost = Decimal(str(cost))
                    logger.info(f"Tier 2 scraping successful (cost: ${cost:.4f})")

                except Exception as tier2_error:
                    logger.error(f"Both scraping tiers failed. Tier 1: {tier1_error}, Tier 2: {tier2_error}")
                    raise Exception(f"All scraping methods failed. Last error: {tier2_error}")

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
            'method': scrape_method,
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
                'content_length': len(html_content),
                'scrape_duration': scrape_duration,
                'method': scrape_method,  # Track which tier was used
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
