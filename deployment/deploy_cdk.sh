#!/bin/bash
# deployment/deploy-cdk.sh
# Deploy Plot Agent using AWS CDK

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REGION="${AWS_REGION:-us-east-1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo -e "${GREEN}Plot Agent AWS CDK Deployment${NC}"
echo "========================================"

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo -e "${RED}Error: AWS CDK not found${NC}"
    echo "Install with: npm install -g aws-cdk"
    exit 1
fi

# Check if in project root
if [ ! -f "deployment/cdk/app.py" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Get AWS Account ID
echo -e "${YELLOW}Getting AWS Account ID...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"

# Step 1: Install CDK dependencies
echo -e "\n${YELLOW}Step 1: Installing CDK dependencies...${NC}"
cd deployment/cdk
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
echo -e "${GREEN}✓ CDK dependencies installed${NC}"

# Step 2: Bootstrap CDK (only needed once per account/region)
echo -e "\n${YELLOW}Step 2: Checking CDK bootstrap...${NC}"
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $REGION &>/dev/null; then
    echo "Bootstrapping CDK (one-time setup)..."
    cdk bootstrap aws://$ACCOUNT_ID/$REGION
    echo -e "${GREEN}✓ CDK bootstrapped${NC}"
else
    echo -e "${GREEN}✓ CDK already bootstrapped${NC}"
fi

# Step 3: Deploy CDK stack
echo -e "\n${YELLOW}Step 3: Deploying CDK stack...${NC}"
cdk deploy --require-approval never
echo -e "${GREEN}✓ CDK stack deployed${NC}"

# Get ECR Repository URI
ECR_REPO=$(aws cloudformation describe-stacks \
  --stack-name PlotAgentStack \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryURI`].OutputValue' \
  --output text)

echo "ECR Repository: $ECR_REPO"

# Step 4: Build and push Docker image
cd ../..
echo -e "\n${YELLOW}Step 4: Logging into ECR...${NC}"
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
echo -e "${GREEN}✓ Logged into ECR${NC}"

echo -e "\n${YELLOW}Step 5: Building Docker image...${NC}"
docker build -f deployment/Dockerfile -t plot-agent:$IMAGE_TAG .
echo -e "${GREEN}✓ Docker image built${NC}"

echo -e "\n${YELLOW}Step 6: Pushing image to ECR...${NC}"
docker tag plot-agent:$IMAGE_TAG $ECR_REPO:$IMAGE_TAG
docker push $ECR_REPO:$IMAGE_TAG
echo -e "${GREEN}✓ Image pushed to ECR${NC}"

# Step 7: Force new deployment
echo -e "\n${YELLOW}Step 7: Updating ECS services...${NC}"
CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name PlotAgentStack \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' \
  --output text)

for SERVICE in plot-agent-regular plot-agent-hitl plot-agent-hitl-test; do
  aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE \
    --force-new-deployment \
    --region $REGION > /dev/null 2>&1 || true
  echo "  - Updated $SERVICE"
done

echo -e "${GREEN}✓ Services updated${NC}"

# Summary
echo -e "\n${GREEN}========================================"
echo "Deployment Complete!"
echo "========================================${NC}"
echo ""
echo "Services are currently STOPPED (0 tasks running)"
echo "To start a service, run:"
echo ""
echo "  ./deployment/start-service.sh regular"
echo "  ./deployment/start-service.sh hitl"
echo "  ./deployment/start-service.sh test"