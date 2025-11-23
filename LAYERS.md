# Lambda Layers Structure

This project uses a clean separation of concerns with two dedicated Lambda layers:

## 📦 **Layers Overview**

### 1. **Shared Code Layer** (`layers/shared_code/`)
- **Purpose**: Custom internal utilities and helpers
- **Contents**: Your application-specific modules
  - `shared/dynamo_helper.py` - DynamoDB operations
  - `shared/s3_helper.py` - S3 operations
  - `shared/logger.py` - Logging utilities
  - `shared/constants.py` - Configuration constants
  - `shared/dynamodb_utils.py` - DynamoDB utilities

**Benefits**:
- ✅ Frequently updated (only your code)
- ✅ Small size = fast deployments
- ✅ Version independently from dependencies
- ✅ Tracked in git (`layers/shared_code/` is included)

### 2. **Dependencies Layer** (`layers/dependencies/`)
- **Purpose**: Third-party Python packages
- **Contents**: All pip-installed packages
  - `boto3`, `botocore` - AWS SDK
  - `requests` - HTTP library
  - `pydantic` - Data validation
  - etc.

**Benefits**:
- ✅ Updated rarely (only when upgrading packages)
- ✅ Large size = built once, reused everywhere
- ✅ NOT tracked in git (packages only, not committed)
- ✅ Rebuilt only when `requirements.txt` changes

### 3. **Detector Layer** (`lambdas/detector_layer/`)
- **Purpose**: Function-specific heavy dependencies
- **Contents**: LLM and parsing libraries
  - `openai` - OpenAI API client
  - `beautifulsoup4` - HTML/XML parser
  - `lxml` - XML processing

**Benefits**:
- ✅ Only attached to detector Lambda (saves space for other functions)
- ✅ Can be updated independently

---

## 🔄 **How Lambda Layers Are Used**

Each Lambda function references layers in order:

```python
# Generic Lambda (get_websites, scraper, predictor)
layers=[self.dependencies_layer, self.shared_code_layer]

# Detector Lambda (also needs LLM packages)
layers=[self.dependencies_layer, self.shared_code_layer, self.detector_layer]
```

When Lambda starts, it adds these to `sys.path` in order.

---

## 📝 **Import Examples**

```python
# Your custom code
from shared.s3_helper import S3Helper
from shared.dynamo_helper import DynamoDBHelper
from shared.logger import get_logger

# Third-party packages
import boto3
import requests
from openai import OpenAI
```

---

## 🚀 **Deployment & Updates**

### **Update Shared Code Only**
```bash
# Changes in layers/shared_code/
$ cdk deploy InfrastructureStack

# ✅ Only shared code layer rebuilt (fast!)
# ✅ Dependencies layer unchanged
```

### **Update Dependencies**
```bash
# Changes in requirements.txt or layer code
$ cd layers/dependencies
$ pip install -r ../../lambdas/shared_layer/requirements.txt -t python/
$ cdk deploy InfrastructureStack

# ✅ Dependencies layer rebuilt (slower, but rare)
```

---

## 📂 **Directory Structure**

```
PromoTracker/
├── layers/
│   ├── shared_code/
│   │   └── python/
│   │       └── shared/
│   │           ├── __init__.py
│   │           ├── dynamo_helper.py
│   │           ├── s3_helper.py
│   │           ├── logger.py
│   │           └── ...
│   └── dependencies/
│       └── python/
│           ├── boto3/
│           ├── requests/
│           ├── pydantic/
│           └── ... (third-party packages)
├── lambdas/
│   ├── scraper/
│   │   └── handler.py
│   ├── detector/
│   │   └── handler.py
│   └── ...
└── infrastructure/
    └── infrastructure_stack.py
```

---

## ✅ **Git Tracking**

- **Included** (tracked in git):
  - `layers/shared_code/` - Your code
  - `layers/dependencies/python/.gitignore` - Marker file only

- **Excluded** (not tracked):
  - `layers/dependencies/python/` content - Third-party packages
  - `lambdas/shared_layer/` - Old structure (deprecated)
  - `lambdas/detector_layer/python/` (except structure)

---

## 🔧 **Best Practices**

1. **Keep shared code small** - Only utilities, not business logic
2. **Update dependencies carefully** - Test compatibility across all Lambdas
3. **Version layers separately** - Use CDK versioning or timestamps
4. **Document new utilities** - Keep `shared/` modules clear and organized
5. **Test locally** - Replicate layer paths locally before deploying

---
