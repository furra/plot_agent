#!/bin/bash
# deployment/cdk-diff.sh
# Show changes that will be deployed

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Showing CDK diff...${NC}"

cd deployment/cdk

if [ ! -d "venv" ]; then
    echo "Installing CDK dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

cdk diff

deactivate
cd ../..

echo ""
echo -e "${GREEN}To deploy these changes, run:${NC}"
echo "  ./deployment/deploy-cdk.sh"