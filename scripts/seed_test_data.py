"""
Script to seed test data into DynamoDB Websites table.
Run this after deploying the infrastructure.
"""
import boto3
import os
import sys

# Sample test websites
TEST_WEBSITES = [
    {
        'website_id': 'johnlewis-uk',
        'name': 'John Lewis & Partners',
        'url': 'https://www.johnlewis.com',
        'enabled': 'true',
        'promotion_selectors': [
            '.promo-banner',
            '.sale-message',
            '[data-test="promotion-banner"]'
        ],
        'category': 'department_store'
    },
    {
        'website_id': 'amazon-uk',
        'name': 'Amazon UK',
        'url': 'https://www.amazon.co.uk',
        'enabled': 'true',
        'promotion_selectors': [
            '#promo-grid',
            '.deals-sash',
            '.badge-wrapper'
        ],
        'category': 'marketplace'
    },
    {
        'website_id': 'currys-uk',
        'name': 'Currys',
        'url': 'https://www.currys.co.uk',
        'enabled': 'true',
        'promotion_selectors': [
            '.promotion-message',
            '.sale-banner'
        ],
        'category': 'electronics'
    },
    {
        'website_id': 'argos-uk',
        'name': 'Argos',
        'url': 'https://www.argos.co.uk',
        'enabled': 'true',
        'promotion_selectors': [
            '.promo-strip',
            '.sale-info'
        ],
        'category': 'general_merchandise'
    },
    {
        'website_id': 'boots-uk',
        'name': 'Boots',
        'url': 'https://www.boots.com',
        'enabled': 'true',
        'promotion_selectors': [
            '.offer-message',
            '.promo-banner'
        ],
        'category': 'health_beauty'
    }
]


def seed_websites(table_name):
    """Seed test websites into DynamoDB."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    print(f"Seeding {len(TEST_WEBSITES)} test websites into {table_name}...")

    for website in TEST_WEBSITES:
        try:
            table.put_item(Item=website)
            print(f"  ✓ Added {website['name']}")
        except Exception as e:
            print(f"  ✗ Failed to add {website['name']}: {str(e)}")

    print("\nSeeding complete!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python seed_test_data.py <WEBSITES_TABLE_NAME>")
        print("\nGet the table name from CDK outputs after deployment.")
        sys.exit(1)

    table_name = sys.argv[1]
    seed_websites(table_name)
