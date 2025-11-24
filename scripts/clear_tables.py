#!/usr/bin/env python3
"""
Script to clear all DynamoDB tables in PromoTracker.
This will delete all items from the tables but keep the table structure intact.
"""
import boto3
import sys
from typing import List, Dict

# Get table names from environment or use defaults
TABLES = [
    'PromoTrackerStack-WebsitesTable-XXXXXX',
    'PromoTrackerStack-PromotionsTable-XXXXXX',
    'PromoTrackerStack-PredictionsTable-XXXXXX',
    'PromoTrackerStack-ScrapingMetricsTable-XXXXXX'
]


def get_table_names() -> List[str]:
    """Get actual table names from DynamoDB."""
    dynamodb = boto3.client('dynamodb', region_name='eu-west-2')
    
    try:
        response = dynamodb.list_tables()
        # Look for tables with Infrastructure or PromoTracker stack naming
        promo_tables = [t for t in response['TableNames'] if 'Infrastructure' in t or 'PromoTracker' in t]
        if not promo_tables:
            raise Exception("No PromoTracker tables found. Make sure infrastructure is deployed.")
        return sorted(promo_tables)
    except Exception as e:
        print(f"Error listing tables: {str(e)}")
        sys.exit(1)


def clear_table(table_name: str) -> int:
    """
    Clear all items from a DynamoDB table.
    
    Args:
        table_name: Name of the table to clear
        
    Returns:
        Number of items deleted
    """
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
    table = dynamodb.Table(table_name)
    
    # Get the key schema
    response = dynamodb.meta.client.describe_table(TableName=table_name)
    key_names = [key['AttributeName'] for key in response['Table']['KeySchema']]
    
    deleted_count = 0
    
    # Scan and delete items in batches
    while True:
        response = table.scan()
        
        if response['Count'] == 0:
            break
        
        # Use batch_write_item to delete items
        with table.batch_writer(overwrite_by_pkeys=key_names) as batch:
            for item in response['Items']:
                key = {key_name: item[key_name] for key_name in key_names}
                batch.delete_item(Key=key)
                deleted_count += 1
        
        # If there are more items, continue scanning
        if 'LastEvaluatedKey' not in response:
            break
    
    return deleted_count


def main():
    """Main function to clear all tables."""
    print("PromoTracker - Clear All Tables\n")
    
    # Get actual table names
    table_names = get_table_names()
    print(f"Found {len(table_names)} PromoTracker table(s):\n")
    for i, name in enumerate(table_names, 1):
        print(f"  {i}. {name}")
    
    # Confirm with user
    print("\n⚠️  WARNING: This will delete ALL items from these tables!")
    response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
    
    if response.lower() != 'yes':
        print("Cancelled. No tables were cleared.")
        sys.exit(0)
    
    print("\nClearing tables...\n")
    
    total_deleted = 0
    for table_name in table_names:
        try:
            count = clear_table(table_name)
            total_deleted += count
            status = "✓" if count > 0 else "✓ (was empty)"
            print(f"{status} {table_name}: {count} items deleted")
        except Exception as e:
            print(f"✗ {table_name}: ERROR - {str(e)}")
    
    print(f"\n✓ Done! Total items deleted: {total_deleted}")


if __name__ == '__main__':
    main()
