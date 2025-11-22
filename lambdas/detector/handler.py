"""
Lambda function to detect promotions from scraped HTML.
Implements Tier 1 (CSS selectors) and Tier 2 (LLM-based detection).
"""
import json
import os
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from openai import OpenAI
from dynamo_helper import DynamoDBHelper
from s3_helper import S3Helper
from logger import get_logger

logger = get_logger(__name__)

# Load OpenAI API key from Parameter Store at container startup
ssm_client = boto3.client('ssm', region_name='eu-west-2')

try:
    response = ssm_client.get_parameter(
        Name='/PromoTracker/OpenAIApiKey',
        WithDecryption=True
    )
    OPENAI_API_KEY = response['Parameter']['Value']
    logger.info("Successfully loaded OpenAI API key from Parameter Store")
except Exception as e:
    logger.warning(f"Failed to load OpenAI API key: {str(e)}")
    OPENAI_API_KEY = None


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


def detect_with_llm(html: str, website_name: str) -> Optional[Dict[str, Any]]:
    """
    Detect promotions using OpenAI GPT (Tier 2 detection).

    Args:
        html: HTML content
        website_name: Name of the website for context

    Returns:
        Dict with promotion details or None if not found
    """
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not available, skipping LLM detection")
        return None

    try:
        # Extract clean text from HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit text to avoid token limits (approximately 12000 characters ~= 3000 tokens for GPT-4o-mini)
        text = text[:12000]

        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Prepare prompt for GPT
        prompt = f"""You are analyzing the website content for {website_name} to detect if there are any active promotions, sales, or special offers.

Website content:
{text}

Please analyze this content and determine if there are any current promotions, sales, discounts, or special offers.

Your response MUST be in JSON format with the following structure:
{{
    "promotion_found": true/false,
    "promotion_text": "exact text of the promotion if found, or empty string if not found",
    "confidence": 0.0-1.0 (your confidence level),
    "reasoning": "brief explanation of your decision"
}}

Only return the JSON object, nothing else."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for cost efficiency
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes website content to detect promotions. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # Parse response
        response_text = response.choices[0].message.content.strip()

        # Try to extract JSON if wrapped in markdown code blocks
        if response_text.startswith('```'):
            # Remove markdown code block markers
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        logger.info(f"LLM detection result: {result}")

        if result.get('promotion_found'):
            return {
                'found': True,
                'method': 'llm_openai',
                'text': result.get('promotion_text', '')[:500],
                'confidence': float(result.get('confidence', 0.8)),
                'reasoning': result.get('reasoning', '')
            }

        return None

    except Exception as e:
        logger.error(f"Error in LLM detection: {str(e)}")
        # Don't raise - allow fallback to continue
        return None


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

        # Try Tier 1: CSS selector detection
        detection_result = None

        if selectors:
            detection_result = detect_with_css_selectors(html_content, selectors)
            if detection_result:
                logger.info(f"Promotion found using CSS selectors for {website_id}")

        # Try Tier 2: LLM detection (fallback if CSS selectors didn't find anything)
        if not detection_result:
            logger.info(f"CSS selectors didn't find promotion for {website_id}, trying LLM detection")
            website_name = website.get('name', website_id)
            detection_result = detect_with_llm(html_content, website_name)
            if detection_result:
                logger.info(f"Promotion found using LLM for {website_id}")

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
