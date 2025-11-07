#!/bin/bash
# setup-cdk.sh
# One-time setup for AWS CDK deployment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Setting up AWS CDK deployment...${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    echo "Install Node.js from: https://nodejs.org/"
    exit 1
fi
echo -e "${GREEN}✓ Node.js installed: $(node --version)${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found${NC}"
    echo "Install with: pip install awscli"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI installed${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials configured${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "Install Docker from: https://www.docker.com/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Install CDK CLI
echo ""
echo -e "${YELLOW}Installing AWS CDK CLI...${NC}"
if ! command -v cdk &> /dev/null; then
    npm install -g aws-cdk
    echo -e "${GREEN}✓ CDK CLI installed${NC}"
else
    echo -e "${GREEN}✓ CDK CLI already installed: $(cdk --version)${NC}"
fi

# Create directory structure
echo ""
echo -e "${YELLOW}Creating deployment directory structure...${NC}"
mkdir -p deployment/cdk

# Generate app requirements.txt
echo ""
echo -e "${YELLOW}Generating requirements.txt...${NC}"
if command -v uv &> /dev/null; then
    uv pip compile pyproject.toml -o deployment/requirements.txt
    echo -e "${GREEN}✓ requirements.txt generated${NC}"
else
    echo -e "${YELLOW}⚠ uv not found. Generate manually:${NC}"
    echo "  uv pip compile pyproject.toml -o deployment/requirements.txt"
fi

# Make scripts executable
echo ""
echo -e "${YELLOW}Making scripts executable...${NC}"
chmod +x deployment/*.sh 2>/dev/null || true
echo -e "${GREEN}✓ Scripts made executable${NC}"

# Create CDK virtualenv and install dependencies
echo ""
echo -e "${YELLOW}Setting up CDK Python environment...${NC}"
cd deployment/cdk
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    deactivate
    echo -e "${GREEN}✓ CDK dependencies installed${NC}"
else
    echo -e "${GREEN}✓ CDK environment already exists${NC}"
fi
cd ../..

# Summary
echo ""
echo -e "${GREEN}========================================"
echo "Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Project structure:"
echo "deployment/"
echo "├── cdk/"
echo "│   ├── app.py              # Infrastructure code"
echo "│   ├── requirements.txt    # CDK dependencies"
echo "│   └── venv/              # Python virtualenv"
echo "├── Dockerfile"
echo "├── requirements.txt        # App dependencies"
echo "└── *.sh                    # Helper scripts"
echo ""
echo "Next steps:"
echo ""
echo "1. Review the CDK stack:"
echo "   ${YELLOW}cat deployment/cdk/app.py${NC}"
echo ""
echo "2. Preview what will be created:"
echo "   ${YELLOW}./deployment/cdk-diff.sh${NC}"
echo ""
echo "3. Deploy to AWS:"
echo "   ${YELLOW}./deployment/deploy-cdk.sh${NC}"
echo ""
echo "4. After deployment, start a service:"
echo "   ${YELLOW}./deployment/start-service.sh regular${NC}"
echo ""
echo "Documentation: deployment/README-CDK.md"
