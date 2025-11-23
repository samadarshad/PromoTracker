"""
DynamoDB utility functions for type conversions.
"""
from decimal import Decimal
from typing import Any, Dict, List, Union


def float_to_decimal(value: Union[float, int, str]) -> Decimal:
    """
    Convert float/int/str to Decimal for DynamoDB compatibility.

    Args:
        value: Number to convert

    Returns:
        Decimal representation
    """
    return Decimal(str(value))


def prepare_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively convert all floats in a dictionary to Decimals for DynamoDB.

    DynamoDB doesn't support Python float types - they must be Decimal.
    This function walks through a dict and converts all floats.

    Args:
        item: Dictionary to convert

    Returns:
        Dictionary with floats converted to Decimals

    Example:
        >>> data = {'price': 19.99, 'count': 5, 'name': 'Product'}
        >>> prepare_dynamodb_item(data)
        {'price': Decimal('19.99'), 'count': 5, 'name': 'Product'}
    """
    result = {}

    for key, value in item.items():
        if isinstance(value, float):
            result[key] = Decimal(str(value))
        elif isinstance(value, dict):
            result[key] = prepare_dynamodb_item(value)
        elif isinstance(value, list):
            result[key] = [
                prepare_dynamodb_item(v) if isinstance(v, dict)
                else Decimal(str(v)) if isinstance(v, float)
                else v
                for v in value
            ]
        else:
            result[key] = value

    return result


def decimal_to_float(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively convert all Decimals in a dictionary to floats.

    Useful when reading from DynamoDB and need to serialize to JSON.

    Args:
        item: Dictionary to convert

    Returns:
        Dictionary with Decimals converted to floats

    Example:
        >>> data = {'price': Decimal('19.99'), 'count': 5}
        >>> decimal_to_float(data)
        {'price': 19.99, 'count': 5}
    """
    result = {}

    for key, value in item.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, dict):
            result[key] = decimal_to_float(value)
        elif isinstance(value, list):
            result[key] = [
                decimal_to_float(v) if isinstance(v, dict)
                else float(v) if isinstance(v, Decimal)
                else v
                for v in value
            ]
        else:
            result[key] = value

    return result
