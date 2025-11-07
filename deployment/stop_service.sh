#!/bin/bash
# deployment/stop-service.sh
# Stop a specific ECS service

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$1" ]; then
  echo -e "${RED}Error: Service name required${NC}"
  echo "Usage: ./stop_service.sh [base|hitl|test|all]"
  exit 1
fi

SERVICE_TYPE=$1
STACK_NAME="PlotAgentStack"
REGION="${AWS_REGION:-us-east-1}"

CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' \
  --output text)

stop_service() {
  local service=$1
  echo -e "${YELLOW}Stopping $service...${NC}"
  aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $service \
    --desired-count 0 \
    --region $REGION > /dev/null
  echo -e "${GREEN}✓ $service stopped${NC}"
}

if [ "$SERVICE_TYPE" == "all" ]; then
  stop_service "plot-agent-base"
  stop_service "plot-agent-hitl"
  stop_service "plot-agent-hitl-test"
else
  case $SERVICE_TYPE in
    base)
      stop_service "plot-agent-base"
      ;;
    hitl)
      stop_service "plot-agent-hitl"
      ;;
    test)
      stop_service "plot-agent-hitl-test"
      ;;
    *)
      echo -e "${RED}Invalid service type: $SERVICE_TYPE${NC}"
      echo "Valid options: base, hitl, test, all"
      exit 1
      ;;
  esac
fi

echo ""
echo "Services stopped. You are no longer being charged for compute."
