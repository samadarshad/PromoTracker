"""
DynamoDB helper utilities for PromoTracker.
"""
import os
import boto3
from typing import Dict, List, Optional, Any
from boto3.dynamodb.conditions import Key, Attr


class DynamoDBHelper:
    """Helper class for DynamoDB operations."""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.websites_table = self.dynamodb.Table(os.environ['WEBSITES_TABLE'])
        self.promotions_table = self.dynamodb.Table(os.environ['PROMOTIONS_TABLE'])
        self.predictions_table = self.dynamodb.Table(os.environ['PREDICTIONS_TABLE'])
        self.metrics_table = self.dynamodb.Table(os.environ['METRICS_TABLE'])

    def get_enabled_websites(self) -> List[Dict[str, Any]]:
        """
        Query all enabled websites from DynamoDB.

        Returns:
            List of website items
        """
        try:
            response = self.websites_table.query(
                IndexName='EnabledWebsitesIndex',
                KeyConditionExpression=Key('enabled').eq('true')
            )
            return response.get('Items', [])
        except Exception as e:
            raise Exception(f"Error querying enabled websites: {str(e)}")

    def get_website(self, website_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific website by ID.

        Args:
            website_id: The website ID

        Returns:
            Website item or None if not found
        """
        try:
            response = self.websites_table.get_item(Key={'website_id': website_id})
            return response.get('Item')
        except Exception as e:
            raise Exception(f"Error getting website {website_id}: {str(e)}")

    def save_promotion(self, promotion_data: Dict[str, Any]) -> None:
        """
        Save promotion data to DynamoDB.

        Args:
            promotion_data: Promotion data to save
        """
        try:
            self.promotions_table.put_item(Item=promotion_data)
        except Exception as e:
            raise Exception(f"Error saving promotion: {str(e)}")

    def get_website_promotions(
        self,
        website_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get promotions for a specific website.

        Args:
            website_id: The website ID
            limit: Maximum number of promotions to return

        Returns:
            List of promotion items
        """
        try:
            response = self.promotions_table.query(
                IndexName='WebsitePromotionsIndex',
                KeyConditionExpression=Key('website_id').eq(website_id),
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            raise Exception(f"Error getting promotions for {website_id}: {str(e)}")

    def save_prediction(self, prediction_data: Dict[str, Any]) -> None:
        """
        Save prediction data to DynamoDB.

        Args:
            prediction_data: Prediction data to save
        """
        try:
            self.predictions_table.put_item(Item=prediction_data)
        except Exception as e:
            raise Exception(f"Error saving prediction: {str(e)}")

    def save_metric(self, metric_data: Dict[str, Any]) -> None:
        """
        Save scraping metric to DynamoDB.

        Args:
            metric_data: Metric data to save
        """
        try:
            self.metrics_table.put_item(Item=metric_data)
        except Exception as e:
            raise Exception(f"Error saving metric: {str(e)}")
