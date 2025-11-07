#!/bin/bash
# deployment/logs.sh
# View logs for a specific service

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$1" ]; then
  echo -e "${RED}Error: Service name required${NC}"
  echo "Usage: ./logs.sh [base|hitl|test]"
  exit 1
fi

SERVICE_TYPE=$1
REGION="${AWS_REGION:-us-east-1}"

case $SERVICE_TYPE in
  base)
    LOG_GROUP="/ecs/plot-agent-base"
    ;;
  hitl)
    LOG_GROUP="/ecs/plot-agent-hitl"
    ;;
  test)
    LOG_GROUP="/ecs/plot-agent-hitl-test"
    ;;
  *)
    echo -e "${RED}Invalid service type: $SERVICE_TYPE${NC}"
    echo "Valid options: base, hitl, test"
    exit 1
    ;;
esac

echo -e "${YELLOW}Streaming logs from $LOG_GROUP...${NC}"
echo "Press Ctrl+C to stop"
echo ""

aws logs tail $LOG_GROUP --follow --region $REGION