#!/bin/bash
# deployment/cdk-destroy.sh
# Destroy the CDK stack and all resources

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}⚠️  WARNING: This will destroy all AWS resources!${NC}"
echo ""
read -p "Are you sure? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Stop all services first
echo -e "${YELLOW}Stopping all services...${NC}"
./deployment/stop-service.sh all

echo -e "${YELLOW}Destroying CDK stack...${NC}"

cd deployment/cdk

if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

cdk destroy --force

deactivate
cd ../..

echo -e "${GREEN}✓ Stack destroyed${NC}"