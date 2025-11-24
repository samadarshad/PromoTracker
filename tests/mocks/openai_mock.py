"""
Mock responses for OpenAI API
Used to simulate OpenAI API responses without making actual API calls
"""

# Successful promotion detection with multiple promotions
PROMOTIONS_FOUND_RESPONSE = {
    "id": "chatcmpl-test123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": """{
    "promotions": [
        {
            "title": "50% Off Summer Collection",
            "description": "Get 50% off all summer items! Limited time offer.",
            "discount_percentage": 50,
            "discount_code": "SUMMER50",
            "valid_until": "2024-07-31",
            "conditions": "Applies to summer collection items only",
            "category": "seasonal"
        },
        {
            "title": "Free Shipping on Orders Over $50",
            "description": "Enjoy free standard shipping on all orders over $50.",
            "discount_percentage": 0,
            "discount_code": null,
            "valid_until": "2024-08-15",
            "conditions": "Minimum order value: $50",
            "category": "shipping"
        },
        {
            "title": "Buy 2 Get 1 Free",
            "description": "Buy any 2 items and get the 3rd item free (equal or lesser value).",
            "discount_percentage": 33,
            "discount_code": "BUY2GET1",
            "valid_until": "2024-07-20",
            "conditions": "Third item must be equal or lesser value",
            "category": "bundle"
        }
    ]
}"""
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
        "total_tokens": 350
    }
}

# No promotions found
NO_PROMOTIONS_RESPONSE = {
    "id": "chatcmpl-test456",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": """{
    "promotions": []
}"""
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110
    }
}

# Single promotion found
SINGLE_PROMOTION_RESPONSE = {
    "id": "chatcmpl-test789",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": """{
    "promotions": [
        {
            "title": "20% Off Everything",
            "description": "Get 20% off all products site-wide",
            "discount_percentage": 20,
            "discount_code": "SAVE20",
            "valid_until": "2024-12-31",
            "conditions": "No minimum purchase required",
            "category": "general"
        }
    ]
}"""
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 120,
        "completion_tokens": 80,
        "total_tokens": 200
    }
}

# Malformed JSON response (to test error handling)
MALFORMED_RESPONSE = {
    "id": "chatcmpl-testABC",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": """{
    "promotions": [
        {
            "title": "Invalid Promotion"
            // Missing closing bracket and other fields
}"""
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120
    }
}

# API error response
API_ERROR_RESPONSE = {
    "error": {
        "message": "Internal server error",
        "type": "server_error",
        "code": "internal_error"
    }
}

# Rate limit error
RATE_LIMIT_ERROR = {
    "error": {
        "message": "Rate limit exceeded",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded"
    }
}

# Authentication error
AUTH_ERROR = {
    "error": {
        "message": "Invalid API key",
        "type": "invalid_request_error",
        "code": "invalid_api_key"
    }
}


def get_mock_response(scenario="promotions_found"):
    """
    Get a mock OpenAI API response for different scenarios

    Args:
        scenario: One of "promotions_found", "no_promotions", "single_promotion",
                  "malformed", "api_error", "rate_limit", "auth_error"

    Returns:
        dict: Mock API response
    """
    responses = {
        "promotions_found": PROMOTIONS_FOUND_RESPONSE,
        "no_promotions": NO_PROMOTIONS_RESPONSE,
        "single_promotion": SINGLE_PROMOTION_RESPONSE,
        "malformed": MALFORMED_RESPONSE,
        "api_error": API_ERROR_RESPONSE,
        "rate_limit": RATE_LIMIT_ERROR,
        "auth_error": AUTH_ERROR
    }
    return responses.get(scenario, PROMOTIONS_FOUND_RESPONSE)


class MockOpenAIResponse:
    """Mock OpenAI response object that matches the openai library's response structure"""

    def __init__(self, response_dict):
        self.id = response_dict.get("id", "")
        self.object = response_dict.get("object", "")
        self.created = response_dict.get("created", 0)
        self.model = response_dict.get("model", "")
        self.choices = [MockChoice(choice) for choice in response_dict.get("choices", [])]
        self.usage = MockUsage(response_dict.get("usage", {}))


class MockChoice:
    """Mock choice object"""

    def __init__(self, choice_dict):
        self.index = choice_dict.get("index", 0)
        self.message = MockMessage(choice_dict.get("message", {}))
        self.finish_reason = choice_dict.get("finish_reason", "")


class MockMessage:
    """Mock message object"""

    def __init__(self, message_dict):
        self.role = message_dict.get("role", "")
        self.content = message_dict.get("content", "")


class MockUsage:
    """Mock usage object"""

    def __init__(self, usage_dict):
        self.prompt_tokens = usage_dict.get("prompt_tokens", 0)
        self.completion_tokens = usage_dict.get("completion_tokens", 0)
        self.total_tokens = usage_dict.get("total_tokens", 0)
