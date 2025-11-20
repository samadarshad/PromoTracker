# Promo Tracker - Project Implementation Roadmap

**Target Timeline:** 4-6 weeks (part-time)  
**Goal:** Production-ready portfolio project demonstrating AWS serverless + AI/ML expertise

---

## Phase 0: Project Setup & Foundation (Days 1-3)

### Infrastructure & Tooling Setup

- [ ] **Initialize Git Repository**
  - [ ] Create GitHub repo with `.gitignore` for Python/Node
  - [ ] Set up branch protection rules (require PR reviews)
  - [ ] Create initial `README.md` with project overview
  - [ ] Add `LICENSE` file (MIT recommended)

- [ ] **Set Up AWS Account & Billing**
  - [ ] Create dedicated AWS account (or use existing with separate IAM user)
  - [ ] Enable billing alerts (set at $2, $5, $10 thresholds)
  - [ ] Configure Cost Explorer and budget tracking
  - [ ] Create IAM user with programmatic access for development
  - [ ] Set up MFA for root account

- [ ] **Local Development Environment**
  - [ ] Install AWS CLI and configure credentials
  - [ ] Install AWS CDK CLI (`npm install -g aws-cdk`)
  - [ ] Install Python 3.11+ and create virtual environment
  - [ ] Install Docker Desktop (for local Lambda testing)
  - [ ] Install AWS SAM CLI (for local Step Functions testing)
  - [ ] Set up VS Code with extensions: Python, AWS Toolkit, DynamoDB

- [ ] **Project Structure**
  - [ ] Create project directory structure:
    ```
    promo-tracker/
    ├── infrastructure/          # CDK code
    ├── lambdas/                 # Lambda function code
    │   ├── get_websites/
    │   ├── scraper/
    │   ├── detector/
    │   ├── predictor/
    │   ├── api/
    │   └── mcp_server/
    ├── frontend/                # React app
    ├── tests/                   # All tests
    │   ├── unit/
    │   ├── integration/
    │   └── fixtures/
    ├── docs/                    # Documentation + diagrams
    ├── scripts/                 # Utility scripts
    └── shared/                  # Shared libraries/utils
    ```
  - [ ] Create `pyproject.toml` for Python dependency management
  - [ ] Create `package.json` for CDK dependencies
  - [ ] Set up `.env.example` for environment variables

- [ ] **Documentation Foundation**
  - [ ] Copy ARCHITECTURE.md to `/docs/`
  - [ ] Create `CONTRIBUTING.md` with development guidelines
  - [ ] Create `SETUP.md` with local development instructions
  - [ ] Create `TODO.md` (this file) for tracking progress

---

## Phase 1: Core Backend - MVP Pipeline (Days 4-10)

**Goal:** Get one website scraped, detected, and stored end-to-end

### 1.1 Infrastructure as Code (CDK)

- [ ] **Initialize CDK Project**
  - [ ] Run `cdk init app --language=typescript` in `/infrastructure/`
  - [ ] Define CDK stacks architecture:
    - [ ] `StorageStack` (DynamoDB tables, S3 buckets)
    - [ ] `PipelineStack` (Step Functions, EventBridge, Lambdas)
    - [ ] `ApiStack` (API Gateway, Lambda functions)
    - [ ] `FrontendStack` (CloudFront, S3 static hosting)
  - [ ] Configure CDK context for dev/prod environments

- [ ] **Storage Stack - DynamoDB Tables**
  - [ ] Create `Websites` table with GSIs
  - [ ] Create `Promotions` table with GSIs
  - [ ] Create `Predictions` table
  - [ ] Create `ScrapingMetrics` table with TTL enabled
  - [ ] Configure point-in-time recovery (PITR)
  - [ ] Set up on-demand billing mode
  - [ ] Add CDK outputs for table names/ARNs

- [ ] **Storage Stack - S3 Buckets**
  - [ ] Create `promo-tracker-html-{env}` bucket
  - [ ] Configure lifecycle policies (Standard → Glacier → Delete)
  - [ ] Enable versioning for compliance
  - [ ] Set up bucket policies (private by default)
  - [ ] Configure CORS for frontend access

- [ ] **Deploy Storage Stack**
  - [ ] Run `cdk deploy StorageStack`
  - [ ] Verify tables in DynamoDB console
  - [ ] Verify S3 bucket created
  - [ ] Document stack outputs

### 1.2 Lambda Functions - Core Logic

- [ ] **Shared Library (`/shared/`)**
  - [ ] Create `dynamodb_helper.py` (CRUD operations)
  - [ ] Create `s3_helper.py` (upload/download utilities)
  - [ ] Create `logger.py` (structured CloudWatch logging)
  - [ ] Create `constants.py` (table names, bucket names from env vars)
  - [ ] Write unit tests for each helper module

- [ ] **Get Websites Lambda**
  - [ ] Implement handler to query DynamoDB Websites table
  - [ ] Add filtering logic for `enabled=true`
  - [ ] Add error handling and logging
  - [ ] Write unit tests (mock DynamoDB responses)
  - [ ] Package with dependencies (boto3)

- [ ] **Scraper Lambda (Tier 1 - Basic HTTP)**
  - [ ] Implement `requests`-based scraper
  - [ ] Add user-agent rotation logic
  - [ ] Add retry logic with exponential backoff
  - [ ] Implement robots.txt checking
  - [ ] Save raw HTML to S3
  - [ ] Update ScrapingMetrics table
  - [ ] Write unit tests with VCR.py for recording HTTP responses
  - [ ] Test against 3 sample websites

- [ ] **Scraper Lambda (Tier 2 - Firecrawl Fallback)**
  - [ ] Sign up for Firecrawl API account
  - [ ] Store API key in AWS Secrets Manager
  - [ ] Implement Firecrawl API integration
  - [ ] Add fallback logic (try basic → fallback to Firecrawl)
  - [ ] Save markdown to S3
  - [ ] Track cost in ScrapingMetrics
  - [ ] Test Firecrawl integration with 1-2 websites

- [ ] **Detector Lambda (Tier 1 - CSS Selectors)**
  - [ ] Implement BeautifulSoup-based detection
  - [ ] Read selectors from website config
  - [ ] Extract promotional text from CSS selectors
  - [ ] Write structured output to DynamoDB
  - [ ] Write unit tests with fixture HTML files

- [ ] **Detector Lambda (Tier 2 - LLM)**
  - [ ] Sign up for Anthropic API (Claude)
  - [ ] Store API key in Secrets Manager
  - [ ] Implement prompt template for promotion detection
  - [ ] Add token optimization (truncate HTML to 4000 chars)
  - [ ] Parse JSON response from Claude
  - [ ] Add confidence scoring logic
  - [ ] Write unit tests with mocked Claude responses
  - [ ] Test with 5 real HTML samples (mix of promos/no promos)

- [ ] **Simple Predictor Lambda (Placeholder for MVP)**
  - [ ] Implement basic "weighted average" logic
  - [ ] Query last 30 days of promotions
  - [ ] Calculate average days between sales
  - [ ] Write prediction to DynamoDB
  - [ ] Add placeholder for Prophet integration (Phase 2)

### 1.3 Step Functions Orchestration

- [ ] **Define State Machine**
  - [ ] Create `statemachine.asl.json` definition
  - [ ] Add "Get Websites" task
  - [ ] Add Map state for parallel processing (max concurrency = 10)
  - [ ] Add Scraper → Detector → Predictor flow per website
  - [ ] Add error handling (Catch blocks with retry)
  - [ ] Add success/failure notifications (CloudWatch)

- [ ] **Deploy Step Functions**
  - [ ] Create IAM role with permissions for Lambda invocations
  - [ ] Deploy state machine via CDK
  - [ ] Test manually with 1 website input
  - [ ] Test with 3 websites to verify parallelism

- [ ] **EventBridge Scheduler**
  - [ ] Create EventBridge rule for daily trigger (09:00 UTC)
  - [ ] Configure rule to invoke Step Functions
  - [ ] Set up IAM role for EventBridge → Step Functions
  - [ ] Test manual trigger from console

### 1.4 MVP Testing & Validation

- [ ] **Seed Test Data**
  - [ ] Create script to populate Websites table with 5 test stores
  - [ ] Include diverse examples (John Lewis, Amazon UK, etc.)
  - [ ] Add sample CSS selectors for each

- [ ] **End-to-End MVP Test**
  - [ ] Trigger Step Functions manually
  - [ ] Verify all 5 websites scraped successfully
  - [ ] Check S3 for HTML/markdown files
  - [ ] Verify DynamoDB Promotions table populated
  - [ ] Verify ScrapingMetrics table updated
  - [ ] Check CloudWatch Logs for errors

- [ ] **Cost Tracking**
  - [ ] Document actual AWS costs after 1 week
  - [ ] Verify free tier usage
  - [ ] Calculate projected monthly costs

---

## Phase 2: Advanced Prediction & API Layer (Days 11-17)

### 2.1 Time Series Forecasting (Prophet)

- [ ] **Research & Prototyping**
  - [ ] Create Jupyter notebook in `/notebooks/`
  - [ ] Generate synthetic historical promotion data (1 year)
  - [ ] Test Prophet with seasonal patterns
  - [ ] Experiment with hyperparameters
  - [ ] Document findings in notebook

- [ ] **Predictor Lambda Upgrade**
  - [ ] Install `prophet` library (may require custom Lambda layer)
  - [ ] Create Lambda layer for Prophet + dependencies
  - [ ] Implement three-tier prediction logic:
    - [ ] Tier 1: Prophet (if 30+ data points)
    - [ ] Tier 2: Weighted average (if 10-29 data points)
    - [ ] Tier 3: Calendar-based heuristic (if <10 data points)
  - [ ] Add model versioning to predictions
  - [ ] Write predictions to DynamoDB with `is_latest` flag
  - [ ] Write unit tests for each prediction tier

- [ ] **Prediction Validation**
  - [ ] Create script to backtest predictions
  - [ ] Calculate MAE (Mean Absolute Error)
  - [ ] Document accuracy metrics
  - [ ] Tune Prophet hyperparameters based on results

### 2.2 REST API Layer

- [ ] **API Lambda Functions**
  - [ ] `GET /stores` - List all stores with predictions
  - [ ] `GET /stores/{id}` - Get single store details
  - [ ] `GET /stores/{id}/history` - Get promotion history
  - [ ] `POST /stores` - Add new store (authenticated)
  - [ ] `DELETE /stores/{id}` - Remove store (authenticated)

- [ ] **API Gateway Setup**
  - [ ] Create REST API in CDK
  - [ ] Configure CORS
  - [ ] Add request validation schemas
  - [ ] Set up rate limiting (100 req/min per IP)
  - [ ] Add API key requirement for POST/DELETE
  - [ ] Deploy to dev stage

- [ ] **Authentication (AWS Cognito)**
  - [ ] Create Cognito User Pool
  - [ ] Configure user attributes (email only)
  - [ ] Set up hosted UI for sign-up/login
  - [ ] Create Cognito authorizer for API Gateway
  - [ ] Test authenticated endpoints

- [ ] **API Testing**
  - [ ] Write integration tests using `pytest` + `requests`
  - [ ] Test all endpoints with valid/invalid inputs
  - [ ] Test authentication flow
  - [ ] Test rate limiting
  - [ ] Document API with Postman collection

### 2.3 MCP Server Implementation

- [ ] **MCP Research & Setup**
  - [ ] Read MCP documentation (https://modelcontextprotocol.io/)
  - [ ] Set up local MCP server for development
  - [ ] Test MCP server with Claude Desktop

- [ ] **MCP Lambda Function**
  - [ ] Create `mcp_server` Lambda
  - [ ] Implement MCP protocol handlers
  - [ ] Define MCP tools:
    - [ ] `get_store_prediction(website_id)` - Get next sale prediction
    - [ ] `compare_stores([website_ids])` - Compare multiple stores
    - [ ] `get_store_history(website_id, limit)` - Get historical sales
    - [ ] `search_stores(query)` - Natural language store search
  - [ ] Share business logic with REST API (use shared modules)
  - [ ] Add structured logging

- [ ] **MCP Deployment**
  - [ ] Deploy MCP Lambda with public URL (or API Gateway)
  - [ ] Configure Claude Desktop to use MCP server
  - [ ] Test all MCP tools via Claude Desktop
  - [ ] Document MCP setup in README

- [ ] **MCP Testing**
  - [ ] Write example conversations (like in Appendix D)
  - [ ] Test error handling (invalid store IDs, etc.)
  - [ ] Verify response formats match expectations

---

## Phase 3: Frontend & User Experience (Days 18-24)

### 3.1 Frontend Development

- [ ] **React App Setup**
  - [ ] Create React app with Vite (`npm create vite@latest`)
  - [ ] Install dependencies: `react-router-dom`, `axios`, `tailwindcss`, `recharts`
  - [ ] Configure Tailwind CSS
  - [ ] Set up routing structure
  - [ ] Configure API client with axios

- [ ] **Core Pages**
  - [ ] **Dashboard** (`/`)
    - [ ] Display all stores in grid/list view
    - [ ] Show prediction countdown ("Next sale in X days")
    - [ ] Add search/filter functionality
    - [ ] Show current promotion status
  - [ ] **Store Detail** (`/stores/:id`)
    - [ ] Show store info and next prediction
    - [ ] Display historical promotion chart (Recharts)
    - [ ] Show prediction confidence interval
    - [ ] Add "Add to Watchlist" functionality
  - [ ] **Add Store** (`/add`)
    - [ ] Form to submit new store URL
    - [ ] Show onboarding progress
    - [ ] Display detected selectors

- [ ] **Authentication UI**
  - [ ] Integrate Cognito Hosted UI
  - [ ] Add login/logout buttons
  - [ ] Protect authenticated routes
  - [ ] Handle token refresh

- [ ] **Responsive Design**
  - [ ] Test on mobile, tablet, desktop
  - [ ] Ensure touch-friendly controls
  - [ ] Add loading states and skeletons
  - [ ] Add error boundaries

### 3.2 Frontend Deployment

- [ ] **S3 Static Hosting**
  - [ ] Create S3 bucket for frontend
  - [ ] Configure bucket for static website hosting
  - [ ] Set up bucket policy for public read access

- [ ] **CloudFront Distribution**
  - [ ] Create CloudFront distribution pointing to S3
  - [ ] Configure custom domain (optional)
  - [ ] Add SSL certificate (AWS Certificate Manager)
  - [ ] Set up cache invalidation on deploy

- [ ] **Build Pipeline**
  - [ ] Create build script (`npm run build`)
  - [ ] Create deploy script (`deploy-frontend.sh`)
  - [ ] Test deployment manually
  - [ ] Verify production site works

---

## Phase 4: Production Readiness (Days 25-30)

### 4.1 Testing & Quality Assurance

- [ ] **Unit Tests (Target: 80% coverage)**
  - [ ] Lambda functions: test each handler independently
  - [ ] Shared libraries: test all helper functions
  - [ ] Frontend: test key components with React Testing Library
  - [ ] Run coverage report: `pytest --cov=lambdas --cov=shared`

- [ ] **Integration Tests**
  - [ ] Test Step Functions execution end-to-end (use SAM)
  - [ ] Test API endpoints with real DynamoDB/S3 (LocalStack)
  - [ ] Test frontend against mocked API

- [ ] **Load Testing**
  - [ ] Use Locust or k6 to simulate 100 concurrent users
  - [ ] Test API Gateway rate limits
  - [ ] Verify Lambda concurrency handling
  - [ ] Document performance results

- [ ] **LLM Accuracy Validation**
  - [ ] Create labeled dataset (50 websites, manually labeled)
  - [ ] Run detector Lambda against dataset
  - [ ] Calculate precision, recall, F1 score
  - [ ] Document accuracy metrics (target: 90%+ F1)

### 4.2 Monitoring & Observability

- [ ] **CloudWatch Dashboards**
  - [ ] Create "System Health" dashboard:
    - [ ] Lambda invocation counts
    - [ ] Lambda error rates
    - [ ] Lambda duration (p50, p95, p99)
    - [ ] API Gateway request count
    - [ ] API Gateway 4xx/5xx errors
    - [ ] DynamoDB read/write capacity
    - [ ] S3 bucket size
  - [ ] Create "Business Metrics" dashboard:
    - [ ] Daily scraping success rate
    - [ ] Promotion detection rate
    - [ ] Prediction accuracy (MAE)
    - [ ] Cost per scrape
    - [ ] Active promotions count

- [ ] **CloudWatch Alarms**
  - [ ] Lambda error rate > 10% (any function)
  - [ ] Scraping success rate < 85%
  - [ ] API Gateway 5xx error rate > 5%
  - [ ] Daily AWS cost > $2
  - [ ] DynamoDB throttling events > 0
  - [ ] Configure SNS topic for email notifications

- [ ] **X-Ray Tracing**
  - [ ] Enable X-Ray on all Lambdas
  - [ ] Add X-Ray annotations for key operations
  - [ ] Create service map
  - [ ] Test tracing through Step Functions workflow

- [ ] **Logging Standards**
  - [ ] Ensure all Lambdas use structured JSON logging
  - [ ] Add correlation IDs across pipeline stages
  - [ ] Create CloudWatch Insights queries for debugging
  - [ ] Document common troubleshooting queries

### 4.3 Security Hardening

- [ ] **IAM Least Privilege**
  - [ ] Audit all IAM roles created by CDK
  - [ ] Remove wildcard permissions (`*`)
  - [ ] Add resource-specific ARNs
  - [ ] Enable MFA for Cognito users

- [ ] **Secrets Management**
  - [ ] Move all API keys to Secrets Manager
  - [ ] Rotate secrets every 90 days (set reminder)
  - [ ] Remove hardcoded secrets from code
  - [ ] Audit code for accidentally committed secrets

- [ ] **API Security**
  - [ ] Add request validation (reject malformed requests)
  - [ ] Implement rate limiting per user (not just per IP)
  - [ ] Add CORS whitelist (specific domains only)
  - [ ] Enable AWS WAF (optional, if budget allows)

- [ ] **Data Privacy**
  - [ ] Add privacy policy page to frontend
  - [ ] Ensure no PII stored in DynamoDB
  - [ ] Add robots.txt compliance check to scraper
  - [ ] Document GDPR considerations

### 4.4 CI/CD Pipeline

- [ ] **GitHub Actions Workflows**
  - [ ] **Test Workflow** (`.github/workflows/test.yml`)
    - [ ] Trigger: on every PR
    - [ ] Run unit tests
    - [ ] Run linters (pylint, black, eslint)
    - [ ] Check code coverage
    - [ ] Fail if coverage < 70%
  
  - [ ] **Deploy Infrastructure** (`.github/workflows/deploy-infra.yml`)
    - [ ] Trigger: on push to `main`
    - [ ] Run `cdk synth`
    - [ ] Run `cdk diff` (show changes)
    - [ ] Run `cdk deploy --all` (with approval)
  
  - [ ] **Deploy Frontend** (`.github/workflows/deploy-frontend.yml`)
    - [ ] Trigger: on push to `main` (changes in `/frontend/`)
    - [ ] Build React app
    - [ ] Sync to S3
    - [ ] Invalidate CloudFront cache

- [ ] **Environment Strategy**
  - [ ] Create `dev` and `prod` AWS accounts (or separate regions)
  - [ ] Configure environment variables in GitHub Secrets
  - [ ] Deploy to `dev` automatically on PR merge
  - [ ] Deploy to `prod` manually with approval

### 4.5 Documentation

- [ ] **Architecture Diagram**
  - [ ] Create visual diagram with draw.io or Lucidchart
  - [ ] Show all AWS services and data flow
  - [ ] Add to `/docs/architecture-diagram.png`
  - [ ] Reference in ARCHITECTURE.md

- [ ] **API Documentation**
  - [ ] Generate OpenAPI spec from API Gateway
  - [ ] Create interactive docs with Swagger UI
  - [ ] Add example requests/responses
  - [ ] Host on GitHub Pages

- [ ] **Runbooks**
  - [ ] Create `RUNBOOK.md` with common operations:
    - [ ] How to add a new website manually
    - [ ] How to debug failed scraping jobs
    - [ ] How to force a prediction recalculation
    - [ ] How to investigate cost spikes
    - [ ] How to roll back a deployment

- [ ] **README Overhaul**
  - [ ] Add badges (build status, coverage, license)
  - [ ] Add GIF/screenshots of frontend
  - [ ] Link to live demo
  - [ ] Add "Features" section highlighting tech stack
  - [ ] Add "Getting Started" guide
  - [ ] Link to architecture docs

---

## Phase 5: Polish & Portfolio Optimization (Days 31-35)

### 5.1 Demo & Screenshots

- [ ] **Create Demo Video**
  - [ ] Record 2-minute walkthrough of system
  - [ ] Show frontend dashboard
  - [ ] Demonstrate MCP integration with Claude
  - [ ] Show Step Functions execution in AWS console
  - [ ] Upload to YouTube/Loom

- [ ] **Screenshots**
  - [ ] Frontend dashboard view
  - [ ] Store detail page with prediction chart
  - [ ] AWS Step Functions execution graph
  - [ ] CloudWatch dashboard
  - [ ] MCP conversation example
  - [ ] Add to `/docs/screenshots/`

### 5.2 Blog Post / Technical Write-Up

- [ ] **Write Blog Post** (publish on Medium/Dev.to)
  - [ ] Title: "Building an AI-Powered E-commerce Sale Tracker with AWS Serverless"
  - [ ] Section 1: Problem statement
  - [ ] Section 2: Architecture overview
  - [ ] Section 3: Cost optimization strategies
  - [ ] Section 4: MCP integration deep dive
  - [ ] Section 5: Lessons learned
  - [ ] Add code snippets and diagrams
  - [ ] Link to GitHub repo

### 5.3 Code Quality

- [ ] **Code Review**
  - [ ] Ensure consistent naming conventions
  - [ ] Add docstrings to all functions
  - [ ] Remove commented-out code
  - [ ] Remove debug print statements
  - [ ] Add type hints (Python 3.11+)

- [ ] **Performance Optimization**
  - [ ] Optimize DynamoDB query patterns (use GSIs)
  - [ ] Reduce Lambda cold start times (trim dependencies)
  - [ ] Optimize S3 storage (compress HTML before upload)
  - [ ] Profile slow Lambda functions

### 5.4 Final Testing

- [ ] **User Acceptance Testing**
  - [ ] Ask 2-3 friends to test the frontend
  - [ ] Collect feedback on UX
  - [ ] Fix critical bugs

- [ ] **Production Smoke Test**
  - [ ] Manually trigger full pipeline
  - [ ] Verify all 30 stores scraped
  - [ ] Check all predictions generated
  - [ ] Test API from frontend
  - [ ] Test MCP tools from Claude Desktop
  - [ ] Verify no errors in CloudWatch

- [ ] **Cost Audit**
  - [ ] Review AWS Cost Explorer for past 30 days
  - [ ] Verify staying under $2/month target
  - [ ] Document actual costs in README

---

## Phase 6: Launch & Iteration (Days 36-42)

### 6.1 Portfolio Integration

- [ ] **GitHub Repo Polish**
  - [ ] Pin repo to GitHub profile
  - [ ] Add detailed README with badges
  - [ ] Add topics/tags (aws, serverless, ai, python, react)
  - [ ] Add LICENSE file
  - [ ] Add CONTRIBUTING.md

- [ ] **Personal Website Update**
  - [ ] Add Promo Tracker to portfolio section
  - [ ] Add link to live demo
  - [ ] Add link to GitHub repo
  - [ ] Add link to blog post

- [ ] **LinkedIn Post**
  - [ ] Write post highlighting key features
  - [ ] Include screenshot and link
  - [ ] Use hashtags: #AWS #Serverless #AI #Python #React

### 6.2 Real-World Usage

- [ ] **Expand Store Coverage**
  - [ ] Add 25 more stores (reach 30 total)
  - [ ] Test with diverse e-commerce sites
  - [ ] Document which sites work best

- [ ] **Monitor for 2 Weeks**
  - [ ] Let system run daily automatically
  - [ ] Track prediction accuracy
  - [ ] Fix bugs as they appear
  - [ ] Tune detection prompts if needed

### 6.3 Optional Enhancements (If Time Allows)

- [ ] **Email Notifications**
  - [ ] Add SNS topic for sale alerts
  - [ ] Allow users to subscribe to specific stores
  - [ ] Send email when prediction is within 3 days

- [ ] **Historical Data Backfill**
  - [ ] Scrape historical sales from Google search
  - [ ] Use News API to find past sale dates
  - [ ] Improve prediction accuracy with more data

- [ ] **Mobile App (React Native)**
  - [ ] Create simple mobile app
  - [ ] Push notifications for sales
  - [ ] Same API as web app

- [ ] **Multi-Region Deployment**
  - [ ] Deploy to eu-west-1 for EU users
  - [ ] Add DynamoDB global tables
  - [ ] Add latency-based routing in Route 53

---

## Success Checklist (Before Calling It "Done")

### Technical Completeness
- [ ] All Lambdas have unit tests (>70% coverage)
- [ ] Step Functions successfully runs daily for 7+ days
- [ ] All API endpoints documented and tested
- [ ] MCP server works with Claude Desktop
- [ ] Frontend deployed and accessible via HTTPS
- [ ] CloudWatch alarms set up and tested
- [ ] Cost stays under $2/month

### Documentation Quality
- [ ] Architecture diagram exists and is referenced
- [ ] README includes setup instructions
- [ ] API documentation is complete
- [ ] Code has meaningful comments and docstrings
- [ ] Blog post published and linked

### Portfolio Readiness
- [ ] GitHub repo has 100+ lines of README
- [ ] Live demo is accessible
- [ ] Demo video recorded and linked
- [ ] Screenshots showcase key features
- [ ] Code is clean and production-quality

### Differentiation for Startups
- [ ] Shows cost consciousness (free tier optimization)
- [ ] Demonstrates AI/ML integration (Claude API)
- [ ] Shows modern tech (MCP, Step Functions, serverless)
- [ ] Includes monitoring and observability
- [ ] Has CI/CD pipeline
- [ ] Demonstrates system design thinking

---
