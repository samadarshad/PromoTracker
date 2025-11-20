# Promo Tracker — Implementation Details

**Author:** Samad Arshad  
**Tech Stack:** Python, AWS Lambda, Step Functions, DynamoDB, S3, LLMs, Firecrawl, Prophet

This document provides implementation-level detail for the Promo Tracker system. It is intended for engineers building, maintaining, or extending the system.

---

# 1. Components

## 1.1 EventBridge Scheduler
- **Schedule:** Daily at 09:00 UTC
- **Target:** Step Functions State Machine
- **Purpose:** Initiate the daily scrape → detect → predict workflow
- **Reliability:** At-least-once delivery; Step Functions handles idempotency

---

## 1.2 Step Functions Orchestrator

### Responsibilities
- Coordinate scraping, detection, and prediction
- Fan-out processing for each website using a **Map State**
- Control concurrency (default: 10 parallel tasks)
- Retry with exponential backoff on transient failures
- Log execution results to CloudWatch

### Workflow Steps
1. Get list of websites  
2. Map over each website  
3. Run scraper Lambda  
4. Run detection Lambda  
5. Run prediction Lambda  
6. Mark execution complete  

---

## 1.3 Get Websites Lambda

### Input
N/A (invoked by Step Functions)

### Output
```json
[
  {
    "website_id": "john_lewis",
    "name": "John Lewis",
    "url": "https://www.johnlewis.com",
    "scrape_config": {
      "selectors": {
        "banner": ".promo-banner",
        "discount_text": ".sale-label"
      },
      "user_agent": "Mozilla/5.0..."
    }
  }
]
```
### Responsibilities
- Query Websites DynamoDB table
- Return only enabled websites
- Pass scrape config to downstream lambdas

## 1.4 Scraper Lambda
### Input
```
{
  "website_id": "john_lewis",
  "url": "https://www.johnlewis.com",
  "scrape_config": {
    "selectors": {...},
    "user_agent": "Mozilla/5.0..."
  }
}
```
### Responsibilities
1. **Try Free HTTP Scraping**
    - Uses custom user agent
    - Times out after 10 seconds
    - Success rate expected ~70–80%

2. **Fallback: Firecrawl API**
    - Handles JS-heavy websites
    - Returns markdown instead of HTML
    - Includes metadata extraction
    - More consistent scraping accuracy (~95%+)

3. Store raw content in S3:

```
s3://promo-tracker-html/scrapes/YYYY/MM/DD/<website>_timestamp_basic.html
s3://promo-tracker-html/scrapes/YYYY/MM/DD/<website>_timestamp_firecrawl.md
```

4. Write scrape metrics to DynamoDB (ScrapingMetrics)

### Output
```
{
  "website_id": "john_lewis",
  "s3_key": "scrapes/2025/11/15/john_lewis_20251115_090132_basic.html",
  "selectors": { ... }
}
```

## 1.5 Promo Detector Lambda
### Input
```
{
  "website_id": "john_lewis",
  "s3_key": "scrapes/2025/11/15/john_lewis_20251115_090132_basic.html",
  "selectors": {
    "banner": ".promo-banner",
    "discount_text": ".sale-label"
  }
}
```
### Responsibilities
**Tier 1: Selector-based Detection (Free)**
- Parse HTML/markdown
- Search banner text using configured selectors
- Look for keywords:
    - sale, discount, %, off, free shipping, promo, deal

**Tier 2: LLM Detection (Paid)**
- Claude Haiku prompt with strict JSON output
- Detects site-wide promotional events
- Extracts:
    - has_promotion
    - promotion_text
    - confidence
    - promotion_type

**Tier 3: Manual Flag**
- Triggered if both above methods fail/ambiguous

### Output (written to PromoHistory)
```
{
  "website_id": "john_lewis",
  "date": "2025-11-15",
  "has_promotion": true,
  "promotion_text": "Black Friday – Up to 50% off",
  "confidence": 0.92,
  "promotion_type": "seasonal_sale",
  "s3_reference": "scrapes/2025/11/15/john_lewis_20251115_090132_basic.html",
  "detected_at": "2025-11-15T09:12:00Z"
}
```
## 1.6 Prediction Engine Lambda
### Input
```
{
  "website_id": "john_lewis"
}
```
### Responsibilities
1. Fetch historical PromoHistory
2. Convert continuous promo periods into sale events
3. Choose prediction strategy based on data availability:

| Events | Strategy                           |
| ------ | ---------------------------------- |
| < 5    | Calendar-based + heuristics        |
| 5–10   | Weighted average + trend detection |
| 10–30  | Prophet (yearly seasonality only)  |
| 30+    | Full Prophet model                 |


4. Write prediction to Predictions table
    - Set is_latest = true
    - Mark old predictions as is_latest = false

### Output
```
{
  "website_id": "john_lewis",
  "prediction_date": "2025-12-15",
  "confidence_lower": "2025-12-08",
  "confidence_upper": "2025-12-22",
  "method": "prophet",
  "data_points_used": 42
}
```

# 2. DynamoDB Schemas
## 2.1 Websites Table
PK: `website_id` (string)

```
{
  "website_id": "john_lewis",
  "name": "John Lewis",
  "url": "https://www.johnlewis.com",
  "scrape_config": {
    "user_agent": "Mozilla/5.0...",
    "selectors": {
      "banner": ".promo-banner",
      "discount_text": ".sale-label"
    }
  },
  "enabled": true,
  "has_promotion": false,
  "last_scraped": "2025-11-14T09:15:32Z",
  "created_at": "2025-10-01T12:00:00Z"
}
```
## 2.2 PromoHistory Table
PK: `website_id`
SK: `date` (YYYY-MM-DD)

```
{
  "website_id": "john_lewis",
  "date": "2025-11-15",
  "has_promotion": true,
  "promotion_text": "Black Friday – Up to 50% off",
  "confidence": 0.92,
  "promotion_type": "seasonal_sale",
  "s3_reference": "...",
  "detected_at": "2025-11-15T09:12:00Z"
}
```

2.3 Predictions Table

PK: `website_id`  
SK: `predicted_at` (ISO 8601 timestamp)

```json
{
  "website_id": "john_lewis",
  "predicted_at": "2025-11-15T09:30:00Z",
  "prediction_date": "2025-12-15",
  "confidence_lower": "2025-12-08",
  "confidence_upper": "2025-12-22",
  "method": "prophet",
  "model_version": "prophet_v2.1",
  "data_points_used": 42,
  "is_latest": true
}
```

**Optional GSI (latest predictions)**  
PK: `is_latest`  
SK: `website_id`

## 2.4 ScrapingMetrics Table

PK: `website_id`  
SK: `timestamp` (YYYYMMDDHHmmss)

```json
{
  "website_id": "john_lewis",
  "timestamp": "20251115_090132",
  "scrape_method": "basic",
  "success": true,
  "cost": 0.0,
  "s3_key": "scrapes/2025/11/15/john_lewis_20251115_090132_basic.html",
  "error_message": null,
  "ttl": 1735603200
}
```

---

# 3. API Specification

**Base URL:**
```
/api
```

## 3.1 GET /stores

**Response:**
```json
{
  "stores": [
    {
      "website_id": "john_lewis",
      "name": "John Lewis",
      "url": "https://www.johnlewis.com",
      "prediction": {
        "prediction_date": "2025-12-15",
        "confidence_lower": "2025-12-08",
        "confidence_upper": "2025-12-22"
      },
      "current_promotion": {
        "active": false,
        "last_active": "2025-11-01"
      }
    }
  ],
  "total": 30
}
```

## 3.2 GET /stores/{website_id}

**Response:**
```json
{
  "website_id": "john_lewis",
  "name": "John Lewis",
  "url": "https://www.johnlewis.com",
  "latest_prediction": {...},
  "current_promotion": {...}
}
```

## 3.3 GET /stores/{website_id}/history?limit=10

**Response:**
```json
{
  "website_id": "john_lewis",
  "history": [
    {
      "date": "2025-11-15",
      "has_promotion": false,
      "detected_at": "2025-11-15T09:15:32Z"
    }
  ]
}
```

## 3.4 POST /stores (Authenticated)

**Request:**
```json
{
  "url": "https://www.example-store.com",
  "name": "Example Store"
}
```

**Response (Success):**
```json
{
  "website_id": "example_store",
  "name": "Example Store",
  "url": "https://www.example-store.com",
  "status": "onboarded",
  "selectors": {
    "banner": ".promo-banner",
    "discount_text": ".sale-label"
  },
  "has_promotion": true,
  "created_at": "2025-11-15T10:30:00Z"
}
```

---

# 4. Website Onboarding Logic

1. Validate URL
2. Generate website_id slug
3. Fetch initial webpage
4. Detect active promotion
5. Extract selectors (if promo found)
6. Save to Websites table
7. Return onboarding result

## ID Generation Rules

- Lowercase
- Replace spaces with underscores
- Remove special characters
- Append numeric suffix if duplicate

---

# 5. S3 Storage Structure

```
promo-tracker-html/
└── scrapes/
    └── YYYY/
        └── MM/
            └── DD/
                ├── <website>_timestamp_basic.html
                └── <website>_timestamp_firecrawl.md
```

**Lifecycle Policy:**
- Standard → Glacier after 90 days
- Delete after 2 years

---

# 6. Error Handling

## Common Errors

| Case | Response |
|------|----------|
| Invalid URL | 400 |
| Duplicate website | 409 |
| Scraper failure | 500 |
| Auth missing for POST | 401 |
| Website disabled | 403 |

## Pipeline Error Isolation

- Failures for one site do not stop the entire Map run
- Step Functions logs per-website context

---

# 7. MCP Integration

## Tools

- `get_stores_list()`
- `get_store_prediction(website_id)`
- `get_store_history(website_id, limit)`
- `search_active_promotions()`
- `compare_stores(website_ids)`

## Response Example

```json
{
  "store_name": "John Lewis",
  "prediction": {
    "date": "2025-12-15",
    "days_until": 30,
    "method": "prophet"
  }
}
```

## Deployment

- Lambda running MCP server
- API key protected
- IAM policy: read-only access to DynamoDB

---

# 8. Logging, Metrics & Monitoring (Implementation View)

## Lambdas

- CloudWatch logs
- X-Ray tracing enabled

## Metrics Tracked

- Basic scrape success rate
- Firecrawl usage + cost
- LLM token cost
- Daily failures per store
- Prediction accuracy (MAE)

## Alarms

- Step Function failure
- Firecrawl spend > $1/month
- LLM spend > $2/day
- No scrape event > 25 hours
- Prediction MAE > 10 days

---

# 9. CI/CD Pipeline

## GitHub Actions

- OIDC → AWS (no long-lived credentials)

### Steps

1. Install dependencies
2. Run tests
3. Deploy CDK stack
4. Smoke test API
5. Roll back on failure

---

# 10. Appendix — Prompt for LLM Detection (Excerpt)

```
You are analyzing an e-commerce website to detect active site-wide promotional sales.
...
Respond ONLY with valid JSON:
{
  "has_promotion": true/false,
  "promotion_text": "...",
  "confidence": 0.0-1.0,
  "promotion_type": "...",
  "reasoning": "..."
}
```