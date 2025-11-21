#!/bin/bash
# Check prerequisites for PromoTracker deployment

echo "🔍 Checking deployment prerequisites..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if all checks pass
ALL_CHECKS_PASSED=true

# Check AWS CLI
echo -n "Checking AWS CLI... "
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    echo -e "${GREEN}✓${NC} $AWS_VERSION"

    # Check if configured
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} AWS credentials configured"
    else
        echo -e "  ${RED}✗${NC} AWS credentials not configured. Run: aws configure"
        ALL_CHECKS_PASSED=false
    fi
else
    echo -e "${RED}✗${NC} Not installed"
    echo "  Install: https://aws.amazon.com/cli/"
    ALL_CHECKS_PASSED=false
fi
echo ""

# Check Node.js
echo -n "Checking Node.js... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Not installed"
    echo "  macOS: brew install node"
    echo "  Windows: Download from nodejs.org"
    echo "  Linux: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    ALL_CHECKS_PASSED=false
fi
echo ""

# Check npm
echo -n "Checking npm... "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} v$NPM_VERSION"
else
    echo -e "${RED}✗${NC} Not installed (comes with Node.js)"
    ALL_CHECKS_PASSED=false
fi
echo ""

# Check AWS CDK CLI
echo -n "Checking AWS CDK CLI... "
if command -v cdk &> /dev/null; then
    CDK_VERSION=$(cdk --version)
    echo -e "${GREEN}✓${NC} $CDK_VERSION"
else
    echo -e "${RED}✗${NC} Not installed"
    echo "  Install: npm install -g aws-cdk"
    ALL_CHECKS_PASSED=false
fi
echo ""

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} $PYTHON_VERSION"

    # Check if version is 3.12+
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
        echo -e "  ${GREEN}✓${NC} Version 3.12+ requirement met"
    else
        echo -e "  ${YELLOW}⚠${NC} Python 3.12+ recommended (you have $PYTHON_VERSION)"
    fi
else
    echo -e "${RED}✗${NC} Not installed"
    ALL_CHECKS_PASSED=false
fi
echo ""

# Check virtual environment
echo -n "Checking Python virtual environment... "
if [ -d "infrastructure/.venv" ]; then
    echo -e "${GREEN}✓${NC} Found"

    # Check if CDK Python library is installed
    if source infrastructure/.venv/bin/activate && python -c "import aws_cdk" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} aws-cdk-lib installed in venv"
    else
        echo -e "  ${YELLOW}⚠${NC} aws-cdk-lib not installed. Run: pip install -r infrastructure/requirements.txt"
    fi
    deactivate 2>/dev/null
else
    echo -e "${YELLOW}⚠${NC} Not found"
    echo "  Create with: cd infrastructure && python3 -m venv .venv"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}✓ All prerequisites met!${NC}"
    echo ""
    echo "Ready to deploy:"
    echo "  cd infrastructure"
    echo "  source .venv/bin/activate"
    echo "  cdk deploy"
else
    echo -e "${RED}✗ Some prerequisites missing${NC}"
    echo ""
    echo "Please install missing dependencies above."
    echo "See DEPLOYMENT.md for detailed instructions."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
