# Lambda Functions

This directory contains all AWS Lambda functions for the PromoTracker pipeline.

## Structure

```
lambdas/
├── shared_layer/           # Shared utilities (Lambda Layer)
│   └── python/
│       ├── dynamo_helper.py  # DynamoDB operations
│       ├── s3_helper.py      # S3 operations
│       ├── logger.py         # Structured logging
│       └── constants.py      # Configuration constants
├── get_websites/           # Lambda: Get enabled websites
│   ├── handler.py
│   └── requirements.txt
├── scraper/                # Lambda: Scrape website HTML
│   ├── handler.py
│   └── requirements.txt
├── detector/               # Lambda: Detect promotions
│   ├── handler.py
│   └── requirements.txt
└── predictor/              # Lambda: Predict next sale
    ├── handler.py
    └── requirements.txt
```

## Lambda Functions

### 1. GetWebsites (`get_websites/`)

**Purpose**: Query DynamoDB for all enabled websites

**Input**:
```json
{}
```

**Output**:
```json
{
  "statusCode": 200,
  "websites": [
    {
      "website_id": "johnlewis-uk",
      "name": "John Lewis",
      "url": "https://www.johnlewis.com",
      "enabled": "true",
      "promotion_selectors": [".promo-banner"]
    }
  ]
}
```

**Environment Variables**:
- `WEBSITES_TABLE`: DynamoDB table name

---

### 2. Scraper (`scraper/`)

**Purpose**: Scrape website HTML and save to S3

**Features**:
- User-agent rotation
- Exponential backoff retry
- robots.txt compliance
- Metrics tracking

**Input**:
```json
{
  "website": {
    "website_id": "johnlewis-uk",
    "url": "https://www.johnlewis.com"
  }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "website_id": "johnlewis-uk",
  "scrape_result": {
    "s3_key": "html/johnlewis-uk/2025-01-21T10:00:00.html",
    "timestamp": "2025-01-21T10:00:00",
    "content_length": 125000,
    "scrape_duration": 2.5
  }
}
```

**Environment Variables**:
- `HTML_BUCKET`: S3 bucket name
- `METRICS_TABLE`: DynamoDB metrics table

---

### 3. Detector (`detector/`)

**Purpose**: Detect promotions from scraped HTML

**Features**:
- CSS selector-based detection (Tier 1)
- BeautifulSoup HTML parsing
- Promotion data persistence

**Input**:
```json
{
  "website": {
    "website_id": "johnlewis-uk",
    "promotion_selectors": [".promo-banner", ".sale-message"]
  },
  "scrape_result": {
    "s3_key": "html/johnlewis-uk/2025-01-21T10:00:00.html"
  }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "website_id": "johnlewis-uk",
  "detection_result": {
    "promotion_found": true,
    "promotion_id": "abc123",
    "promotion_text": "Up to 50% off selected items",
    "confidence": 0.9
  }
}
```

**Environment Variables**:
- `HTML_BUCKET`: S3 bucket name
- `PROMOTIONS_TABLE`: DynamoDB promotions table

---

### 4. Predictor (`predictor/`)

**Purpose**: Predict next promotion date using historical data

**Features**:
- Weighted average prediction (Tier 1)
- Calendar heuristic fallback
- Confidence scoring

**Input**:
```json
{
  "website": {
    "website_id": "johnlewis-uk"
  },
  "detection_result": {
    "promotion_found": true
  }
}
```

**Output**:
```json
{
  "statusCode": 200,
  "website_id": "johnlewis-uk",
  "prediction": {
    "predicted_date": "2025-02-15T00:00:00",
    "days_until_next": 25,
    "prediction_method": "weighted_average",
    "confidence": 0.7,
    "data_points_used": 15
  }
}
```

**Environment Variables**:
- `PROMOTIONS_TABLE`: DynamoDB promotions table
- `PREDICTIONS_TABLE`: DynamoDB predictions table

---

## Shared Layer

The `shared_layer` contains common utilities used across all Lambda functions:

### `dynamo_helper.py`

Provides DynamoDB operations:
- `get_enabled_websites()`: Query enabled websites
- `get_website(website_id)`: Get specific website
- `save_promotion(data)`: Save promotion record
- `get_website_promotions(website_id)`: Get promotion history
- `save_prediction(data)`: Save prediction
- `save_metric(data)`: Save scraping metric

### `s3_helper.py`

Provides S3 operations:
- `upload_html(website_id, content, timestamp)`: Upload HTML to S3
- `download_html(s3_key)`: Download HTML from S3
- `get_latest_html(website_id)`: Get most recent HTML

### `logger.py`

Structured JSON logging for CloudWatch:
- `get_logger(name)`: Get configured logger
- Automatic JSON formatting
- Correlation ID support

### `constants.py`

Configuration constants:
- User agents for scraping
- Request timeouts and retries
- Prediction thresholds

---

## Local Testing

### 1. Install Dependencies

Each Lambda function has its own `requirements.txt`:

```bash
cd get_websites
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export WEBSITES_TABLE=your-table-name
export PROMOTIONS_TABLE=your-table-name
export PREDICTIONS_TABLE=your-table-name
export METRICS_TABLE=your-table-name
export HTML_BUCKET=your-bucket-name
```

### 3. Test Locally

```python
from handler import lambda_handler

event = {"website": {"website_id": "test", "url": "https://example.com"}}
context = {}
result = lambda_handler(event, context)
print(result)
```

---

## Deployment

Lambda functions are deployed automatically by CDK. The `infrastructure_stack.py` references these directories:

```python
lambda_.Function(
    self, "ScraperFunction",
    code=lambda_.Code.from_asset("../lambdas/scraper"),
    ...
)
```

When you run `cdk deploy`, CDK automatically:
1. Packages each Lambda directory
2. Uploads to S3
3. Creates Lambda functions
4. Attaches the shared layer

---

## Future Enhancements

- [ ] **Scraper**: Add Firecrawl API fallback (Tier 2)
- [ ] **Detector**: Add LLM-based detection with Claude API (Tier 2)
- [ ] **Predictor**: Implement Prophet time series forecasting (Tier 2)
- [ ] **API Lambda**: Add REST API handlers for frontend
- [ ] **MCP Lambda**: Add MCP server for Claude Desktop integration

---

## Monitoring

View Lambda logs in CloudWatch:

```bash
# Tail logs for a specific function
aws logs tail /aws/lambda/InfrastructureStack-ScraperFunction --follow

# Search logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/InfrastructureStack-ScraperFunction \
  --filter-pattern "ERROR"
```

---

## Performance

Current configuration:
- **GetWebsites**: 256 MB, 30s timeout
- **Scraper**: 512 MB, 300s timeout
- **Detector**: 1024 MB, 300s timeout
- **Predictor**: 1024 MB, 300s timeout

Adjust in `infrastructure_stack.py` if needed.
