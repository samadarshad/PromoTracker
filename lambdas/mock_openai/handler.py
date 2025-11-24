"""
Mock OpenAI API endpoint for testing
Returns mock chat completion responses without calling real OpenAI API
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Mock OpenAI chat completions API endpoint
    Returns test promotion detection responses
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        messages = body.get('messages', [])

        logger.info(f"Mock OpenAI API called with {len(messages)} messages")

        # Extract user message to determine response
        user_message = ""
        for msg in messages:
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        # Return mock successful response with promotion detection
        # This simulates OpenAI's response format
        mock_promotion_data = {
            "promotion_found": True,
            "promotion_text": "50% Off Summer Collection - Get 50% off all summer items with code SUMMER50. Valid until 2024-12-31.",
            "confidence": 0.95,
            "reasoning": "Clear promotion found with specific discount percentage, code, and validity period."
        }

        response_data = {
            "id": "chatcmpl-mock123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(mock_promotion_data)
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 80,
                "total_tokens": 230
            }
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
        logger.error(f"Mock OpenAI API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "error": {
                    "message": f"Mock server error: {str(e)}",
                    "type": "server_error",
                    "code": "internal_error"
                }
            })
        }
