# Promo Tracker
## Architecture Document

**Written By:** Samad Arshad, Full Stack Engineer  
**Tech Stack:** Python, AWS (Lambda, Step Functions, DynamoDB, S3), LLMs, Time Series ML, MCP

---

## Executive Summary

Promo Tracker is a serverless, event-driven system that scrapes e-commerce websites daily, uses AI to detect promotional sales, and predicts when future sales will occur. Built entirely on AWS free tier to demonstrate proficiency in cloud architecture, Python, and AI/ML for startup portfolio.

**Architecture Highlights:**
- Event-driven pipeline using Step Functions with Map State for parallelism
- Cost-optimized fallback strategies at every layer (scraping, detection, prediction)
- LLM-powered promotion detection with Firecrawl markdown optimization
- Modern serverless stack: $0 AWS infrastructure cost, only pay for external APIs
- MCP (Model Context Protocol) server for natural language data access


---

## Requirements

### Functional Requirements
1. **Daily Data Collection**: Scrape 30 e-commerce websites to detect active promotional sales
2. **AI-Powered Detection**: Use LLMs to identify promotions from raw HTML/text
3. **Predictive Analytics**: Forecast when the next sale will occur based on historical patterns
4. **User Interface**: Display predictions and historical data via web application
5. **Data Persistence**: Store raw HTML, structured promo data, and predictions
6. **Conversational AI Access**: Enable Claude to query predictions naturally via MCP

### Non-Functional Requirements
1. **Cost**: Must run on AWS free tier (~$0/month) indefinitely
2. **Reliability**: 95% success rate for daily scraping jobs
3. **Scalability**: Support 30 stores initially, design for 1000+ stores
4. **Data Volume**: ~30MB currently, ~3GB over 10 years
5. **Latency**: API responses < 500ms, prediction updates within 5 minutes
6. **Maintainability**: Infrastructure as Code (IaC), automated deployments

### Success Metrics
- **Prediction Accuracy**: Mean Absolute Error < 7 days for 90-day forecasts
- **Scraping Success Rate**: > 95% of daily jobs complete successfully
- **System Availability**: 99.5% uptime for API
- **Cost**: Stay within $2/month (for external API calls only)

---

## Overall Architecture

### High-Level System Design

![Promo Tracker AWS Architecture](./docs/architecture-diagram.png)
*Figure 1: Overall AWS Architecture showing Collection & Prediction Pipeline, User Serving Layer, and MCP Integration*

The system consists of three loosely-coupled subsystems:

1. **Collection & Prediction Pipeline** (Event-Driven)
   - Triggered daily via EventBridge
   - Orchestrated by AWS Step Functions
   - Processes 30 websites in parallel
   - Stores results in S3 and DynamoDB

2. **User Serving Layer** (Request-Response)
   - Static React frontend on S3/CloudFront
   - AWS Cognito for user authentication
   - REST API via API Gateway + Lambda
   - Public GET endpoints, authenticated POST endpoints
   - Reads from and writes to DynamoDB

3. **MCP Integration Layer** (Conversational AI)
   - MCP server (Lambda or standalone process)
   - Exposes tools for Claude to query predictions
   - Enables natural language store queries
   - Shared business logic with REST API

### Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Orchestration** | AWS Step Functions | Visual workflow, built-in retry logic, state management |
| **Compute** | AWS Lambda | Pay-per-execution, auto-scaling, 1M free requests/month |
| **Scheduling** | EventBridge | Free for scheduled rules, reliable cron execution |
| **Database** | DynamoDB | NoSQL for flexible schema, 25GB free tier, single-digit ms latency |
| **Object Storage** | S3 + Glacier | Cheap long-term storage for raw HTML archives |
| **AI/ML** | Claude API (Haiku) | Fast, cheap LLM for promotion detection (~$0.50/month) |
| **Forecasting** | Prophet | Battle-tested time series libraries, no external API costs |
| **Frontend** | React + Tailwind | Modern UI, S3 static hosting is free |
| **API** | API Gateway + Lambda | Serverless REST API, 1M free requests/month |
| **Authentication** | AWS Cognito | User authentication, 50K MAUs free tier |
| **MCP Server** | Lambda (Python) | Serverless MCP endpoint, reuses existing business logic |
| **Monitoring** | CloudWatch + X-Ray | Native AWS observability, free tier sufficient |

---

## Detailed Component Design

### 1. Collection & Prediction Pipeline

#### 1.1 EventBridge Scheduler
**Service:** AWS EventBridge  
**Trigger:** Daily at 09:00 UTC  

**Purpose:** Initiates the daily scraping workflow by triggering the Step Functions state machine.

---

#### 1.2 Main Orchestrator (Step Functions)

**Service:** AWS Step Functions (Standard Workflows)  

**Key Design Decisions:**
- **Map State for Parallelism**: Processes 30 websites concurrently (limited to 10 at a time to avoid rate limiting)
- **Retry Strategy**: Exponential backoff for transient failures (network issues, rate limits)
- **Error Isolation**: One website failure doesn't crash entire pipeline
- **Observability**: Each step logs to CloudWatch, Step Functions console shows visual execution graph


---

#### 1.3 Get Websites Lambda

**Responsibilities:**
- Query DynamoDB `Websites` table
- Return list of website metadata (URL, selectors, scraping config)
- Filter out disabled websites
- Initiates a sub-flow for each website using the Step Functions Map state for parallel processing
- Passes website context to each sub-flow: `website_id`, `url`, `name`, and `scrape_config` (including CSS selectors and user agent)

**DynamoDB Schema (Websites Table):**
```json
{
  "website_id": "john_lewis",  // Partition Key
  "name": "John Lewis",
  "url": "https://www.johnlewis.com/",
  "scrape_config": {
    "user_agent": "Mozilla/5.0...",
    "selectors": {
      "banner": ".promo-banner",
      "discount_text": ".sale-label"
    }
  },
  "enabled": true,
  "last_scraped": "2025-11-14T09:15:32Z"
}
```

---

#### 1.4 Website Scraper Lambda

**Execution Context:** Runs within the Step Functions Map state sub-flow for each website

**Input:** Receives from message: `website_id`, `url`, and `user_agent` (if available from scrape_config)

**Responsibilities:**
- Attempt basic HTTP scraping first (free)
- Fall back to paid scraping API if blocked/rate-limited
- Store raw HTML in S3
- Track scraping method and costs
- Return S3 reference for downstream processing

**Output:** Passes to Detector Lambda: `s3_key`, `website_id`, and `selectors` (CSS selectors from scrape_config)

**Two-Tier Scraping Strategy:**

The scraper uses a **cost-optimized fallback approach**:

1. **Tier 1: Basic Free Scraping** (Try first)
   - Direct HTTP requests
   - Custom headers and user agents
   - Respects robots.txt
   - Success rate: ~70-80% for most e-commerce sites
   - Cost: $0

2. **Tier 2: Firecrawl API** (Fallback if Tier 1 fails)
   - Firecrawl handles JS rendering, proxies, and anti-bot bypass
   - **Returns clean markdown** instead of raw HTML (easier for LLM processing)
   - Extracts structured data automatically
   - Built-in rate limiting and retry logic
   - Success rate: ~95%+
   - Cost: ~$0.002 per scrape ($0.60/month if 30% of requests fail to basic scraping)

**Why Firecrawl?**
- **LLM-optimized output**: Returns markdown instead of HTML, reducing Claude token usage by ~60%
- **Better for AI workflows**: Designed for AI scraping use cases
- **Structured extraction**: Can extract specific elements (promotional banners) without BeautifulSoup
- **Modern API**: Better documentation, webhooks, real-time status updates
- **Metadata extraction**: Automatically extracts page title, description, language
- **Cost**: Slightly higher per request ($0.002 vs $0.001) but saves on LLM tokens, making it net cheaper

**Rate Limiting Strategy:**
- Step Function Map State controls concurrency (max 10 parallel)
- Exponential backoff on 429 (Too Many Requests) responses for retries
- Rotate user agents to avoid fingerprinting

**S3 Storage Structure:**
```
s3://promo-tracker-html/
├── scrapes/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── 15/
│   │   │   │   ├── john_lewis_20251115_090132_basic.html
│   │   │   │   ├── amazon_uk_20251115_090145_firecrawl.md
│   │   │   │   └── ...
```
*Note: Firecrawl scrapes stored as `.md` (markdown) instead of `.html`*

**S3 Lifecycle Policy:**
- Keep in Standard storage for 30 days
- Move to Glacier after 90 days (for compliance/debugging)
- Delete after 2 years


**DynamoDB Schema (ScrapingMetrics Table):**
```json
{
  "website_id": "john_lewis",          // Partition Key
  "timestamp": "20251115_090132",      // Sort Key
  "scrape_method": "basic",            // or "firecrawl"
  "success": true,
  "cost": 0.0,                         // 0.0 for basic, 0.002 for Firecrawl
  "s3_key": "scrapes/2025/11/15/john_lewis_20251115_090132_basic.html",
  "error_message": "string (nullable)",
  "ttl": 1735603200                    // Unix timestamp for automatic deletion (90 days)
}
```

**Time-To-Live (TTL) Configuration:**
- **Attribute:** `ttl` (Number, Unix timestamp)
- **Expiration:** 90 days after creation
- **Purpose:** Automatically delete old metrics to reduce storage costs
- **Cost savings:** Keeps table <100 MB, well within free tier


**Why 90 Days?**
- Sufficient for debugging recent scraping issues
- Long enough for monthly cost analysis
- Keeps table size manageable (< 100 MB for 1,000 stores)
- DynamoDB TTL is free (no additional charges)

**Monitoring & Alerts:**

CloudWatch metrics to track:
- `BasicScrapeSuccessRate` - Should stay above 70%
- `FirecrawlUsageCount` - Track paid scrape volume
- `FirecrawlCost` - Alert if > $1.00/month
- `TotalScrapeFailures` - Alert if > 5% failure rate

If basic scrape success rate drops below 60% for a specific site, consider always using Firecrawl for that specific site (store preference in DynamoDB).

---

#### 1.5 Promo Detector Lambda (Three-Tier Detection)

**Execution Context:** Runs within the Step Functions Map state sub-flow for each website, receives S3 reference from Scraper Lambda

**Input:** Receives from message: `s3_key` (scraped content location), `website_id`, and `selectors` (CSS selectors for Tier 1 detection)

**Responsibilities:**
- Fetch content from S3 (HTML or markdown)
- **Tier 1**: Attempt CSS selector-based detection (free, fast)
- **Tier 2**: Fall back to LLM detection if selectors fail (paid, accurate)
- **Tier 3**: Flag for manual review if both fail (rare)
- Parse detection results into structured data
- Store result in DynamoDB

**Output:** Passes to Prediction Engine Lambda: `website_id`

**Three-Tier Detection Strategy:**

The detector uses a **cost-optimized cascade** approach:

1. **Tier 1: CSS Selector Detection (Free)**
   - Check if configured selectors find promotional elements
   - Look for keywords: "sale", "off", "discount", "promo", "%"
   - Success rate: ~40-60% (when promotions are in expected locations)
   - Cost: $0

2. **Tier 2: LLM Detection (Paid)**
   - Use Claude Haiku API for intelligent content analysis
   - Handles varied promotional language and layouts
   - Filters out false negatives from Tier 1
   - Success rate: ~95%+
   - Cost: ~$0.0005 per request
   - **Learning mechanism**: Stores the promotional text and discovered selectors in DynamoDB so Tier 1 can use them in future runs

3. **Tier 3: Manual Review Flag (Fallback)**
   - Triggered when both Tier 1 and Tier 2 fail or return uncertain results
   - Mark as "unknown" with confidence: 0.0
   - Send alert for human verification
   - Rare: <5% of cases
   - Cost: $0


**Enhanced LLM Prompt (with Few-Shot Examples):**

```
You are analyzing an e-commerce website to detect SITE-WIDE promotional sales.

STRICT RULES:
1. SITE-WIDE ONLY (applies to entire catalog or most products)
2. IGNORE product-specific discounts
3. IGNORE marketing emails/newsletters content
4. IGNORE "sign up for discounts" CTAs

POSITIVE EXAMPLES (return has_promotion: true):
- "BLACK FRIDAY: 50% OFF EVERYTHING"
- "Free shipping on all orders this week"
- "20% off your entire purchase with code SAVE20"
- "Summer Sale - Up to 70% off sitewide"
- "Clearance: Everything must go!"

NEGATIVE EXAMPLES (return has_promotion: false):
- "This laptop is 15% off" (product-specific)
- "Join our mailing list for exclusive deals" (not active)
- "Select items on sale" (not site-wide)
- "Save more with our credit card" (requires signup)
- "Daily deals on featured products" (limited selection)

CONTENT (markdown/HTML, first 2000 chars):
{text}

RESPOND WITH JSON ONLY (no markdown, no explanation, no code blocks):
{
  "has_promotion": true or false,
  "promotion_text": "exact text from content" or null,
  "confidence": 0.0 to 1.0,
  "promotion_type": "percentage_off" | "fixed_discount" | "seasonal_sale" | "free_shipping" | "other" | null,
  "reasoning": "brief explanation (max 30 words)"
}

CRITICAL: Your entire response must be ONLY the JSON object above. Do not include markdown code blocks, explanations, or any text outside the JSON structure.
```

**DynamoDB Schema (PromoHistory Table):**
```json
{
  "website_id": "john_lewis",         // Partition Key
  "date": "2025-11-15",               // Sort Key
  "has_promotion": true,
  "promotion_text": "Black Friday Sale - Up to 50% off",
  "confidence": 0.95,
  "promotion_type": "seasonal_sale",
  "s3_reference": "scrapes/2025/11/15/john_lewis_20251115_090132.html",
  "detected_at": "2025-11-15T09:15:32Z"
}
```

---

#### 1.6 Prediction Engine Lambda

**Execution Context:** Runs within the Step Functions Map state sub-flow for each website, after detection completes

**Input:** Receives from message: `website_id`

**Responsibilities:**
- Query historical promo data from DynamoDB
- Prepare time series data
- Train/update forecasting model
- Generate prediction for next sale date
- Store prediction in DynamoDB

**ML Approach: Facebook Prophet**

**Why Prophet:**
- Designed for time series with seasonality (perfect for retail sales)
- Handles missing data gracefully
- Works with limited historical data (cold start problem)
- No external API costs
- Battle-tested by Facebook for forecasting

**Prediction Strategy (Handling Limited Data):**
The prediction engine processes PromoHistory records chronologically, grouping consecutive days with `has_promotion = true` into sale events, then uses the start date of each sale event for forecasting.

The system uses a tiered approach based on available historical data:

**Tier 1: Very Limited Data (< 5 sale events)**
- **Calendar-based prediction**: Use known retail sale seasons (Black Friday, Boxing Day, Summer Sales, etc.)
- **Industry benchmarks**: Fall back to average sale frequency for e-commerce (typically 45-60 days between major sales)
- **Pattern detection**: Analyze existing sale events for patterns (e.g., always on weekends, month-end, specific weekdays)
- **Confidence**: Low (0.3-0.5), with wide confidence intervals (±14 days)

**Tier 2: Limited Data (5-10 sale events)**
- **Weighted averaging**: Calculate average gap between sale events, giving more weight to recent sales
- **Trend analysis**: Detect if sale frequency is increasing/decreasing over time
- **Seasonal hints**: If data spans multiple months, detect monthly/quarterly patterns
- **Confidence**: Medium (0.5-0.7), with moderate confidence intervals (±10 days)

**Tier 3: Moderate Data (10-30 sale events)**
- **Prophet with simplified settings**: Use Prophet but disable complex seasonality
- **Yearly seasonality only**: Focus on annual patterns (Black Friday, Christmas, etc.)
- **Confidence**: Medium-High (0.7-0.85), with tighter intervals (±7 days)

**Tier 4: Rich Data (30+ sale events)**
- **Full Prophet model**: Enable yearly and weekly seasonality
- **Holiday effects**: Include known retail holidays as regressors
- **Confidence**: High (0.85-0.95), with precise intervals (±5 days)


**DynamoDB Schema (Predictions Table):**
```json
{
  "website_id": "john_lewis",         // Partition Key
  "predicted_at": "2025-11-15T09:30:00Z", // Sort Key (enables versioning)
  "prediction_date": "2025-12-15",
  "confidence_lower": "2025-12-08",
  "confidence_upper": "2025-12-22",
  "method": "prophet",
  "model_version": "prophet_v2.1",
  "data_points_used": 45,
  "is_latest": true  // Boolean flag for current prediction
}
```

**Why Versioning?**

The `predicted_at` sort key enables tracking prediction changes over time:
- **Track accuracy**: Compare predictions made on different dates to actual outcomes
- **A/B test models**: Run Prophet vs. other models and compare results
- **Debug changes**: Understand why a prediction changed from one run to the next
- **Historical analysis**: See how predictions evolved as more data was collected

**Implementation Notes:**
- Query latest prediction: Use `is_latest = true` filter
- Track accuracy: Compare old predictions (where `prediction_date < today`) to actual PromoHistory
- When creating new prediction: Set old prediction's `is_latest` to `false`, new one to `true`

**GSI for Latest Predictions (Optional):**
```
GSI Name: LatestPredictionsIndex
Partition Key: is_latest (Boolean)
Sort Key: website_id
Purpose: Quickly fetch all latest predictions across stores
```

---

### 2. User Serving Layer

#### 2.1 Frontend (React SPA)

**Hosting:** S3 Static Website + CloudFront CDN  
**Framework:** React 18 + Tailwind CSS

**Features:**
- Store listing with current promotion status
- Predicted next sale date with confidence intervals
- Historical sale calendar view
- Responsive design for mobile/desktop
- **Add Website Form** (authenticated users only):
  - Login button/form using AWS Cognito (redirects to Cognito Hosted UI)
  - After authentication, "Add Store" button appears
  - Modal form with fields: Website URL (required), Store Name (optional)
  - Form submission calls `POST /stores` with JWT token in Authorization header
  - Shows loading state during onboarding process (scraping + AI detection)
  - Displays success message with extracted selectors, or error if onboarding fails
  - New store immediately appears in store listing

---

#### 2.2 API Gateway

**Type:** REST API  
**Authentication:** 
- GET endpoints: None (public read-only)
- POST endpoints: AWS Cognito User Pool (JWT token required)

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stores` | List all stores with latest predictions |
| GET | `/stores/{id}` | Get store details |
| GET | `/stores/{id}/history` | Get historical promotions |
| GET | `/stores/{id}/prediction` | Get latest prediction |
| POST | `/stores` | Onboard a new store (requires authentication) |

---

#### 2.3 Query Service Lambdas

**Responsibilities:**
- Handle all API Gateway read requests
- Route (internally) based on request path
- Query DynamoDB efficiently (with in-memory caching)
- Format responses as JSON
- Return CORS headers for browser access

#### 2.4 Website Onboarding Process

**Trigger:** Manual user input via API (`POST /stores`)

**Authentication:** AWS Cognito User Pool (JWT token in Authorization header)

**Request Format:**
```json
POST /stores
Content-Type: application/json
Authorization: Bearer <cognito-jwt-token>

{
  "url": "https://www.example-store.com",
  "name": "Example Store"  // Optional: AI will generate if not provided
}
```

**Response Format:**
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
  "has_promotion": true,  // Current promotion status
  "created_at": "2025-11-15T10:30:00Z"
}
```

**Lambda Function:** `onboard_store`

**Flow:**
1. User provides website URL
2. AI generates `website_id` and `name` (if not provided) using the rules above
3. System scrapes website (basic → Firecrawl fallback)
4. AI analyzes content:
   - Detects if promotion currently active
   - Extracts CSS selectors if promotion found
5. Stores configuration in DynamoDB `Websites` table
6. Website ready for daily pipeline

**Smart Detection:**
- If promo found → Extract CSS selectors for fast future detection
- If no promo → Selectors remain null, will use AI detection
- If CSS found later → Automatically updates selectors for faster detection


**Website ID Generation:**

The `website_id` is generated from the website name using the following rules:
1. Convert the name to lowercase
2. Replace spaces with underscores
3. Remove special characters (keep only alphanumeric and underscores)
4. Ensure uniqueness (append a number if duplicate exists, e.g., `amazon_2`)

**Examples:**
- "John Lewis" → `john_lewis`
- "Amazon UK" → `amazon_uk`
- "M&S" → `ms`
- "ASOS.com" → `asos_com`

The `website_id` serves as a stable, URL-friendly identifier used across all tables and as the partition key for efficient DynamoDB queries.

**Why String IDs?**

Slugified string IDs (e.g., `john_lewis`) instead of numeric IDs provide:
- **Self-documenting**: Immediately readable in logs and API responses
- **URL-friendly**: Direct use in REST endpoints without encoding
- **Cross-environment consistency**: Same ID in dev/staging/prod
- **No mapping needed**: Eliminates lookup tables

**Error Handling:**
- Unauthorized: Returns 401 if JWT token is missing or invalid
- Forbidden: Returns 403 if user lacks permissions
- Invalid URL: Returns 400 with error message
- Scraping failure: Returns 500 with retry suggestion
- Duplicate website: Returns 409 with existing `website_id`
- Timeout: Returns 504 if scraping takes > 5 minutes

---

### 3. MCP Integration Layer

**Why MCP for Promo Tracker?**

MCP enables **conversational data access**—users can ask Claude natural language questions about store predictions without visiting the web interface:

**Traditional Workflow:**
```
User: "When is the next John Lewis sale?"
  ↓
User manually visits promo-tracker.com
  ↓
User reads prediction
```

**With MCP:**
```
User: "When is the next John Lewis sale?"
  ↓
Claude automatically calls MCP tool: get_store_prediction("john_lewis")
  ↓
Claude: "Based on historical patterns, John Lewis typically has a sale 
         around December 15, 2025 (±7 days). Their last sale was on 
         November 11 (Veterans Day)."
```

#### 3.1 MCP Server Implementation

**Deployment:** AWS Lambda

**Responsibilities:**
- Expose Promo Tracker data to Claude via standardized MCP protocol
- Provide natural language interface to predictions and historical data
- Enable conversational store comparisons and analysis
- Log MCP usage for analytics
- Reuse existing business logic from REST API

**Tools Exposed:**

1. **`get_stores_list()`**
   - Returns list of all tracked stores with prediction summary
   - Parameters: None
   - Use case: "Show me all stores you track"

2. **`get_store_prediction(website_id: str)`**
   - Returns next sale prediction for specific store
   - Parameters: website_id (e.g., "john_lewis")
   - Use case: "When is the next John Lewis sale?"

3. **`get_store_history(website_id: str, limit: int = 10)`**
   - Returns historical promotion data
   - Parameters: website_id, optional limit
   - Use case: "Show me John Lewis's sale history"

4. **`search_active_promotions()`**
   - Returns all stores currently running sales
   - Parameters: None
   - Use case: "Which stores are having sales right now?"

5. **`compare_stores(website_ids: list[str])`**
   - Compares predictions across multiple stores
   - Parameters: list of website IDs
   - Use case: "Compare Amazon, John Lewis, and ASOS"

**Resources Exposed:**

- **`promo-tracker://stores`** - Read-only store catalog
- **`promo-tracker://predictions`** - Latest predictions for all stores
- **`promo-tracker://active-promotions`** - Current promotional sales

#### 3.2 MCP Use Cases

**1. Conversational Store Queries**

**User:** "Which stores are most likely to have a sale this week?"

**Claude (via MCP):**
- Calls: `get_stores_list()`
- Filters for predictions within 7 days
- Returns: "John Lewis (3 days), ASOS (5 days), Amazon UK (6 days)"

**2. Historical Analysis**

**User:** "How often does John Lewis have sales?"

**Claude (via MCP):**
- Calls: `get_store_history("john_lewis", limit=365)`
- Calculates: Average 45 days between sales
- Returns: "John Lewis typically runs a major sale every 45 days..."

**3. Multi-Store Comparison**

**User:** "Compare Amazon, John Lewis, and ASOS—who's having a sale soonest?"

**Claude (via MCP):**
- Calls: `compare_stores(["amazon_uk", "john_lewis", "asos"])`
- Returns sorted list with confidence intervals

**4. Shopping Assistant Workflow**

**User:** "I want to buy a new TV. Which stores should I wait for?"

**Claude:**
1. Calls `search_active_promotions()` → "No active sales right now"
2. Calls `get_stores_list()` → Gets prediction dates
3. Filters for electronics retailers
4. Returns: "Wait 5 days—John Lewis likely having a sale on Nov 20"

#### 3.3 Configuration & Deployment

**Security:**
- MCP endpoint requires API key authentication
- Read-only access to data (no write operations)
- Same IAM policies as REST API (DynamoDB GetItem/Query only)

**Monitoring:**
- Log all MCP tool invocations to CloudWatch
- Track which tools are used most frequently
- Alert on error rates > 5%
- Monitor API key usage for abuse detection


---

## Infrastructure as Code

**Tool:** AWS CDK (Python)

**Benefits:**
- Version-controlled infrastructure
- Type-safe resource definitions
- Automated deployments
- Easy environment replication (dev/staging/prod)

---

## CI/CD Pipeline

### GitHub Actions Workflow

**Key Features:**
- **OIDC authentication**: No long-lived AWS credentials stored in GitHub
- **Multi-stage pipeline**: Test → Deploy → Smoke Test
- **Automated rollback**: Triggers on deployment failure
- **Code coverage**: Tracks test coverage over time

---

## Monitoring & Observability

### CloudWatch Dashboards

**Custom Dashboard Widgets:**
1. **Pipeline Health**
   - Step Function execution success rate
   - Average execution duration
   - Failed website count per day

2. **Scraping Metrics**
   - HTTP status code distribution
   - Response time percentiles (p50, p95, p99)
   - Rate limit hits

3. **AI Performance**
   - LLM API latency
   - Promotion detection rate (% of sites with active promos)
   - Confidence score distribution

4. **Cost Tracking**
   - Lambda invocation count
   - Claude API spend
   - Firecrawl API spend
   - S3 storage growth

5. **MCP Usage**
   - Tool invocation frequency
   - Error rate
   - API key usage

6. **Prediction Accuracy**
   - Mean Absolute Error (MAE) over time
   - Predictions within ±7 days (target: 80%)
   - Predictions within ±14 days (target: 95%)
   - Accuracy by store (identify problematic stores)
   - Accuracy by prediction method (Prophet vs. calendar-based)

**Prediction Accuracy Calculation:**

A Lambda function runs weekly to calculate accuracy:
1. Query Predictions table for predictions where `prediction_date < today`
2. Query PromoHistory for actual sale dates
3. Calculate: `|predicted_date - actual_date|` for each prediction
4. Aggregate: MAE, percentage within ±7 days, percentage within ±14 days
5. Store metrics in DynamoDB `AccuracyMetrics` table
6. Publish to CloudWatch for dashboard visualization
7. Alert if MAE > 10 days or accuracy < 70%

### Alerting

**SNS Topics:**
- `promo-tracker-critical` - Pipeline failures, database errors
- `promo-tracker-warnings` - High error rates, slow responses

**CloudWatch Alarms:**
```yaml
Alarms:
  - Name: "HighStepFunctionFailureRate"
    Metric: "ExecutionsFailed"
    Threshold: 3 failures in 1 day
    Action: SNS notification
  
  - Name: "BasicScrapeSuccessRateLow"
    Metric: "BasicScrapeSuccessRate"
    Threshold: < 70%
    Action: SNS notification
    Description: "Alert if basic scraping success rate drops below 70%"
  
  - Name: "TotalScrapeFailuresHigh"
    Metric: "TotalScrapeFailures"
    Threshold: > 5% failure rate
    Action: SNS notification
    Description: "Alert if overall scraping failure rate exceeds 5%"
  
  - Name: "FirecrawlCostSpike"
    Metric: "FirecrawlCost"
    Threshold: > $1.00 in 1 month
    Action: SNS notification
    Description: "Alert if Firecrawl API costs exceed monthly budget"
  
  - Name: "LLMCostSpike"
    Metric: "AnthropicAPISpend"
    Threshold: > $2 in 24 hours
    Action: SNS notification + pause scraping
  
  - Name: "MCPErrorRateHigh"
    Metric: "MCPToolErrors"
    Threshold: > 5% error rate
    Action: SNS notification
  
  - Name: "PredictionAccuracyDegrading"
    Metric: "MeanAbsoluteError"
    Threshold: MAE > 10 days OR accuracy < 70%
    Action: SNS notification + flag for model retraining
  
  - Name: "DataFreshnessSLA"
    Metric: "TimeSinceLastScrape"
    Threshold: > 25 hours
    Action: SNS critical alert
    Description: "Alert if any store hasn't been scraped in >25 hours (should be daily)"
```

### X-Ray Tracing

- Trace full request path through Step Functions → Lambda → DynamoDB
- Identify bottlenecks (e.g., slow DynamoDB queries, LLM API latency)
- Debug intermittent failures
- Track MCP tool execution paths


---

## Appendix A: DynamoDB Schema Design

### Table 1: Websites
```
Partition Key: website_id (String)
Attributes:
  - name: String
  - url: String
  - scrape_config: Map
    - user_agent: String
    - selectors: Map
      - banner: String (CSS selector, nullable)
      - discount_text: String (CSS selector, nullable)
  - enabled: Boolean
  - status: String ("onboarded" | "active" | "disabled")
  - has_promotion: Boolean (current promotion status, nullable)
  - last_scraped: String (ISO 8601, nullable)
  - created_at: String (ISO 8601)
```

### Table 2: PromoHistory
```
Partition Key: website_id (String)
Sort Key: date (String, YYYY-MM-DD format)
Attributes:
  - has_promotion: Boolean
  - promotion_text: String (nullable)
  - confidence: Number
  - promotion_type: String (nullable)
  - s3_reference: String
  - detected_at: String (ISO 8601)
```

### Table 3: Predictions
```
Partition Key: website_id (String)
Sort Key: predicted_at (String, ISO 8601 format)
Attributes:
  - prediction_date: String (YYYY-MM-DD)
  - confidence_lower: String (YYYY-MM-DD)
  - confidence_upper: String (YYYY-MM-DD)
  - method: String ("prophet" | "weighted_average" | "calendar_based")
  - model_version: String
  - data_points_used: Number
  - is_latest: Boolean (flag for current prediction)
```

### Table 4: ScrapingMetrics
```
Partition Key: website_id (String)
Sort Key: timestamp (String, YYYYMMDDHHmmss format)
Attributes:
  - scrape_method: String (basic | firecrawl)
    - "basic": Free HTTP scraping
    - "firecrawl": Paid Firecrawl API fallback
  - success: Boolean
  - cost: Number (0.0 for basic, 0.002 for firecrawl)
  - s3_key: String
  - error_message: String (nullable)
  - ttl: Number (Unix timestamp for automatic deletion after 90 days)
```

---

## Appendix B: Sample API Responses

### GET /stores
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
        "confidence_upper": "2025-12-22",
        "days_until": 30,
        "confidence": "medium"
      },
      "current_promotion": {
        "active": false,
        "last_active": "2025-11-01"
      }
    }
  ],
  "total": 30,
  "timestamp": "2025-11-15T10:30:00Z"
}
```

### POST /stores
**Request:**
```json
{
  "url": "https://www.example-store.com",
  "name": "Example Store"
}
```

**Response (Success - 201 Created):**
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

**Response (Error - 409 Conflict):**
```json
{
  "error": "Website already exists",
  "website_id": "example_store",
  "message": "A store with this URL is already being tracked"
}
```

**Response (Error - 400 Bad Request):**
```json
{
  "error": "Invalid URL",
  "message": "URL must be a valid HTTP/HTTPS URL"
}
```

**Response (Error - 401 Unauthorized):**
```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid authentication token"
}
```

### GET /stores/john_lewis/history?limit=10
```json
{
  "website_id": "john_lewis",
  "history": [
    {
      "date": "2025-11-15",
      "has_promotion": false,
      "detected_at": "2025-11-15T09:15:32Z"
    },
    {
      "date": "2025-11-14",
      "has_promotion": false,
      "detected_at": "2025-11-14T09:14:18Z"
    },
    {
      "date": "2025-11-11",
      "has_promotion": true,
      "promotion_text": "Veterans Day Sale - 40% off",
      "promotion_type": "seasonal_sale",
      "confidence": 0.94,
      "detected_at": "2025-11-11T09:12:45Z"
    }
  ],
  "total_records": 365
}
```

### MCP Response: get_store_prediction("john_lewis")
```json
{
  "store_name": "John Lewis",
  "website_id": "john_lewis",
  "prediction": {
    "date": "2025-12-15",
    "confidence_lower": "2025-12-08",
    "confidence_upper": "2025-12-22",
    "days_until": 30,
    "method": "prophet",
    "data_points_used": 45
  }
}
```

---

## Appendix C: Prompt Templates

### Promotion Detection Prompt (Full Version)
```
You are an expert at analyzing e-commerce websites to detect promotional sales. 

Your task: Determine if the website currently has an active SITE-WIDE promotional sale.

IMPORTANT RULES:
1. SITE-WIDE ONLY: Identify sales that apply to the entire store or most products (e.g., "20% off everything", "Black Friday Sale", "Free shipping on all orders")
2. IGNORE PRODUCT-SPECIFIC: Do not flag individual product discounts (e.g., "This laptop is 15% off")
3. LOOK FOR INDICATORS:
   - Banner text with sale messaging
   - Hero section promotional content
   - Site-wide discount codes
   - Seasonal sale announcements (Black Friday, Christmas, etc.)
   - Free shipping promotions
4. CONFIDENCE SCORING:
   - 0.9-1.0: Clear, unambiguous promotional banner
   - 0.7-0.89: Strong indicators but some ambiguity
   - 0.5-0.69: Weak signals or unclear messaging
   - 0.0-0.49: No promotion or product-specific only

HTML CONTENT (first 4000 characters, focused on headers/banners):
{html_text}

RESPOND ONLY WITH VALID JSON (no markdown, no explanation):
{{
  "has_promotion": true or false,
  "promotion_text": "exact text found from HTML" or null,
  "confidence": 0.0 to 1.0,
  "promotion_type": "percentage_off" | "fixed_discount" | "seasonal_sale" | "free_shipping" | "other" | null,
  "reasoning": "brief explanation (50 words max)"
}}
```

---

## Appendix D: MCP Sample Conversations

### Example 1: Simple Query

**User:** "When is the next sale at John Lewis?"

**Claude:** *[Calls `get_store_prediction("john_lewis")`]*

**Response:**
> Based on historical patterns, John Lewis is predicted to have their next sale around **December 15, 2025** (with a confidence range of December 8-22). This prediction is based on 45 historical sale events and uses the Prophet forecasting model. Their last sale was on November 11 (Veterans Day).

---

### Example 2: Comparison

**User:** "I need a new laptop. Compare Amazon, John Lewis, and Currys—who's having a sale first?"

**Claude:** *[Calls `compare_stores(["amazon_uk", "john_lewis", "currys"])`]*

**Response:**
> Here's the comparison:
> 
> 1. **Amazon UK** - Next sale predicted: December 12, 2025 (in 27 days)
> 2. **John Lewis** - Next sale predicted: December 15, 2025 (in 30 days)
> 3. **Currys** - Next sale predicted: December 20, 2025 (in 35 days)
> 
> Amazon UK is likely to have the first sale. Would you like me to check their historical laptop discounts specifically?

---

### Example 3: Historical Analysis

**User:** "How reliable are these predictions? Show me John Lewis's actual sale dates vs. predictions."

**Claude:** *[Calls `get_store_history("john_lewis", limit=50)` and compares to past predictions]*

**Response:**
> Over the past 50 sales, predictions for John Lewis have been:
> - Within ±7 days: 78% accurate
> - Within ±14 days: 92% accurate
> 
> Recent examples:
> - Predicted: Nov 10-12, Actual: Nov 11 ✅
> - Predicted: Oct 15-20, Actual: Oct 18 ✅
> - Predicted: Sep 8-14, Actual: Sep 20 ⚠️ (off by 6 days)
> 
> The system is most accurate for seasonal sales (Black Friday, Boxing Day) and less accurate for surprise flash sales.

---
