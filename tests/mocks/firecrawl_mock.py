"""
Mock responses for Firecrawl API
Used to simulate Firecrawl API responses without making actual API calls
"""

# Successful scrape response
SUCCESSFUL_SCRAPE_RESPONSE = {
    "success": True,
    "data": {
        "markdown": """# ACME Store - Summer Sale

## Current Promotions

### 50% Off Summer Collection
Get 50% off all summer items! Limited time offer.

**Details:**
- Discount: 50%
- Valid until: July 31, 2024
- Code: SUMMER50

### Free Shipping on Orders Over $50
Enjoy free standard shipping on all orders over $50.

**Details:**
- Minimum order: $50
- Valid until: August 15, 2024
- No code needed

### Buy 2 Get 1 Free
Buy any 2 items and get the 3rd item free (equal or lesser value).

**Details:**
- Applies to: All items
- Valid until: July 20, 2024
- Code: BUY2GET1
""",
        "html": "<html><body><h1>ACME Store - Summer Sale</h1><p>Get 50% off all summer items!</p></body></html>",
        "metadata": {
            "title": "ACME Store - Summer Sale",
            "description": "Summer sale with up to 50% off",
            "language": "en",
            "sourceURL": "https://example.com/promotions"
        }
    }
}

# Scrape with no promotions
NO_PROMOTIONS_RESPONSE = {
    "success": True,
    "data": {
        "markdown": """# ACME Store

Welcome to ACME Store. Check out our latest products.

## New Arrivals
- Product A
- Product B
- Product C

## About Us
We are committed to quality and customer satisfaction.
""",
        "html": "<html><body><h1>ACME Store</h1><p>Welcome to our store</p></body></html>",
        "metadata": {
            "title": "ACME Store",
            "description": "Quality products for everyone",
            "language": "en",
            "sourceURL": "https://example.com"
        }
    }
}

# Rate limit error (429)
RATE_LIMIT_RESPONSE = {
    "success": False,
    "error": "Rate limit exceeded. Please try again later.",
    "code": "RATE_LIMIT_EXCEEDED"
}

# API error (500)
API_ERROR_RESPONSE = {
    "success": False,
    "error": "Internal server error",
    "code": "INTERNAL_ERROR"
}

# Invalid URL response
INVALID_URL_RESPONSE = {
    "success": False,
    "error": "Invalid URL provided",
    "code": "INVALID_URL"
}

# Timeout error
TIMEOUT_RESPONSE = {
    "success": False,
    "error": "Request timeout",
    "code": "TIMEOUT"
}


def get_mock_response(scenario="success"):
    """
    Get a mock Firecrawl API response for different scenarios

    Args:
        scenario: One of "success", "no_promotions", "rate_limit", "api_error",
                  "invalid_url", "timeout"

    Returns:
        dict: Mock API response
    """
    responses = {
        "success": SUCCESSFUL_SCRAPE_RESPONSE,
        "no_promotions": NO_PROMOTIONS_RESPONSE,
        "rate_limit": RATE_LIMIT_RESPONSE,
        "api_error": API_ERROR_RESPONSE,
        "invalid_url": INVALID_URL_RESPONSE,
        "timeout": TIMEOUT_RESPONSE
    }
    return responses.get(scenario, SUCCESSFUL_SCRAPE_RESPONSE)
