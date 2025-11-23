"""
S3 helper utilities for PromoTracker.
"""
import os
import boto3
from typing import Optional


class S3Helper:
    """Helper class for S3 operations."""

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket_name = os.environ['HTML_BUCKET']

    def upload_markdown(
        self,
        website_id: str,
        content: str,
        timestamp: str
    ) -> str:
        """
        Upload markdown content to S3.

        Args:
            website_id: The website ID
            content: Markdown content to upload
            timestamp: Timestamp for the file

        Returns:
            S3 key of uploaded file
        """
        key = f"scrapes/{website_id}/{timestamp}.md"

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType='text/markdown'
            )
            return key
        except Exception as e:
            raise Exception(f"Error uploading to S3: {str(e)}")

    def download_html(self, s3_key: str) -> str:
        """
        Download content from S3 (HTML, markdown, or other text formats).

        Args:
            s3_key: S3 key of the file

        Returns:
            Content as string
        """
        try:
            response = self.s3.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Error downloading from S3: {str(e)}")

    def get_latest_html(self, website_id: str) -> Optional[str]:
        """
        Get the latest content file for a website (markdown or HTML).

        Args:
            website_id: The website ID

        Returns:
            Content as string or None if not found
        """
        try:
            prefix = f"scrapes/{website_id}/"
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                return None

            latest_key = response['Contents'][0]['Key']
            return self.download_html(latest_key)
        except Exception as e:
            raise Exception(f"Error getting latest content: {str(e)}")
