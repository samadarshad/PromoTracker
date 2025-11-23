"""
Constants and configuration for PromoTracker.
"""
import os

# DynamoDB Table Names
WEBSITES_TABLE = os.environ.get('WEBSITES_TABLE', '')
PROMOTIONS_TABLE = os.environ.get('PROMOTIONS_TABLE', '')
PREDICTIONS_TABLE = os.environ.get('PREDICTIONS_TABLE', '')
METRICS_TABLE = os.environ.get('METRICS_TABLE', '')

# S3 Bucket Names
HTML_BUCKET = os.environ.get('HTML_BUCKET', '')

# Prediction Configuration
MIN_DATA_POINTS_PROPHET = 30
MIN_DATA_POINTS_WEIGHTED = 10
PREDICTION_DAYS_LOOKBACK = 90
