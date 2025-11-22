# Promo Tracker — Architecture Overview

**Author:** Samad Arshad  
**Tech:** Python, AWS (Lambda, Step Functions, DynamoDB, S3, CloudFront), LLMs, Time Series ML  

---

# 1. Executive Summary

Promo Tracker is a **serverless, cost-optimized system** that scrapes e-commerce websites daily, detects active promotional sales using AI, and predicts when future sales will occur.

The system includes:
- A **daily collection & prediction pipeline** (AWS Step Functions)
- A **public API + UI** for browsing predictions
- An **MCP integration layer** enabling conversational access through AI agents

The architecture demonstrates cloud design, LLM integration, data engineering, and cost-efficient serverless design.

---

# 2. Core Requirements

## Functional
1. Daily scrape ~30 websites  
2. Detect promotions via selectors or LLM  
3. Forecast next sale using time-series modelling  
4. Provide web UI and REST API  
5. Store scrapes, detection results, and predictions  
6. Enable conversational querying via MCP  

## Non-Functional
- **Cost:** Run on AWS free tier (<$2/mo external APIs)  
- **Scalability:** Up to 1000+ websites  
- **Reliability:** ≥95% pipeline success  
- **Latency:** API < 500ms  
- **Maintainability:** IaC + CI/CD  

---

# 3. High-Level Architecture

![Promo Tracker Architecture Diagram](docs/architecture-diagram.png)

## Subsystems

### 1. Collection & Prediction Pipeline
- Scheduled daily via EventBridge  
- Step Functions orchestrate scraping → detection → prediction  
- Parallel processing using Map State  
- S3 for raw scrapes, DynamoDB for structured results  

### 2. User Serving Layer
- React UI hosted on S3 + CloudFront  
- API Gateway + Lambda for REST endpoints  
- Public GETs, authenticated POST for onboarding  
- Reads/writes to DynamoDB  

### 3. MCP Integration Layer
- Lambda-based MCP server  
- Exposes tools such as:  
  - `get_store_prediction`  
  - `search_active_promotions`  
  - `compare_stores`  
- Enables natural-language queries powered by Claude  

---

# 4. Data Flow Overview

## 1. Daily Pipeline
1. **EventBridge** triggers workflow  
2. **Get Websites Lambda** loads configuration  
3. **Map State** fans out tasks  
4. **Scraper Lambda**  
   - Firecrawl API scraping with markdown output  
   - Extract main content only  
   - Store in S3  
5. **Promo Detector Lambda**  
   - Tier 1: CSS selectors  
   - Tier 2: LLM detection  
   - Tier 3: Fallback/manual flag  
   - Write to `PromoHistory`  
6. **Prediction Engine Lambda**  
   - Choose model (Prophet or heuristic)  
   - Write forecast to `Predictions`  

## 2. User API
API Gateway → Lambda → DynamoDB  
Endpoints include: list stores, get history, get prediction.

## 3. Onboarding Flow
- Authenticated POST `/stores`  
- Immediate scrape + detection  
- Extract selectors  
- Add new configuration to `Websites` table  

---

# 5. Key Design Choices

### Serverless Everything
- No servers, auto-scaling, nearly free

### Step Functions for Orchestration
- Visual workflows  
- Retry logic  
- Ideal for fan-out pipelines  

### DynamoDB as Primary Database
- Simple schema  
- Low-latency lookups  
- Free tier friendly  

### Firecrawl Scraping
- Uses Firecrawl API v2 with markdown output  
- Reduces LLM processing costs (markdown vs. raw HTML)  
- Handles JavaScript-rendered content  
- Consistent accuracy (~95%+)

### Three-Tier Detection
1. Selectors (free)  
2. LLM detection (fallback)  
3. Manual flag (rare)

### Prediction Strategy
- Prophet for rich data  
- Heuristics for early cold starts  
- Versioned predictions for accuracy tracking  

---

# 6. Data Model (Simplified)

### Websites
Configuration and scrape settings.

### PromoHistory
Daily detection results.

### Predictions
Forecasts for next sale (versioned).

### ScrapingMetrics
Scraping method, success rate, and cost data.

---

# 7. Monitoring & Reliability

### Dashboards
- Pipeline health  
- Scrape success rate  
- LLM usage & cost  
- Prediction accuracy  
- MCP tool usage  

### Alerts
- Pipeline failures  
- Scrape success drop  
- LLM/Firecrawl cost spikes  
- Stale data (no scrape > 25h)  
- Model accuracy degradation  

---

# 8. Scalability

Designed to scale to **1000+ websites**:
- Controlled concurrency in Map State  
- Selector learning reduces LLM usage  
- Even partitioning across DynamoDB  
- Stateless Lambdas for horizontal scaling  

---

# 9. MCP Integration

AI assistants can query predictions and historical data.

Tools provided:
- `get_stores_list()`  
- `get_store_prediction(id)`  
- `search_active_promotions()`  
- `compare_stores([...])`  

Example natural language workflow:
> “Which stores are predicted to have a sale this week?”

MCP calls internal tools, then responds conversationally.

---

# 10. Conclusion

Promo Tracker is a **production-grade, low-cost, serverless architecture** designed for scalability, maintainability, and AI integration. It demonstrates the ability to design complex, reliable systems using AWS, Python, LLMs, and time-series modelling — ideal for showcasing full-stack backend engineering expertise.

