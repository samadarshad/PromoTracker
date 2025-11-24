"""
Mock Firecrawl API endpoint for testing
Returns mock scraping responses without calling real Firecrawl API
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Mock Firecrawl v2 API endpoint
    Returns test markdown content for any URL
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        url = body.get('url', 'unknown')

        logger.info(f"Mock Firecrawl API called for URL: {url}")

        # Return mock successful response
        response_data = {
            "success": True,
            "data": {
                "markdown": f"""# Test Website - {url}

## Current Promotions

### 50% Off Summer Collection
Get 50% off all summer items! Limited time offer.

**Details:**
- Discount: 50%
- Valid until: 2024-12-31
- Code: SUMMER50

### Free Shipping on Orders Over $50
Enjoy free standard shipping on all orders over $50.

**Details:**
- Minimum order: $50
- Valid until: 2024-12-31
- No code needed

### Buy 2 Get 1 Free
Buy any 2 items and get the 3rd item free (equal or lesser value).

**Details:**
- Applies to: All items
- Valid until: 2024-12-15
- Code: BUY2GET1
""",
                "html": "<html><body><h1>Test content</h1></body></html>",
                "metadata": {
                    "title": "Test Website",
                    "description": "Mock scrape response",
                    "sourceURL": url
                }
            },
            "creditsUsed": 1
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }

    except Exception as e:
        logger.error(f"Mock Firecrawl API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "success": False,
                "error": f"Mock server error: {str(e)}"
            })
        }
