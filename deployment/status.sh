#!/bin/bash
# deployment/status.sh
# Check status of all services

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

STACK_NAME="PlotAgentStack"
REGION="${AWS_REGION:-us-east-1}"

echo -e "${GREEN}Plot Agent Service Status${NC}"
echo "========================================"

CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$CLUSTER_NAME" ]; then
  echo -e "${RED}Stack not found. Run ./deploy_cdk.sh first.${NC}"
  exit 1
fi

check_service() {
  local service=$1
  local display_name=$2

  local running=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $service \
    --region $REGION \
    --query 'services[0].runningCount' \
    --output text 2>/dev/null)

  if [ "$running" == "1" ]; then
    TASK_ARN=$(aws ecs list-tasks \
      --cluster $CLUSTER_NAME \
      --service-name $service \
      --region $REGION \
      --query 'taskArns[0]' \
      --output text)

    if [ "$TASK_ARN" != "None" ] && [ -n "$TASK_ARN" ]; then
      ENI_ID=$(aws ecs describe-tasks \
        --cluster $CLUSTER_NAME \
        --tasks $TASK_ARN \
        --region $REGION \
        --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
        --output text)

      PUBLIC_IP=$(aws ec2 describe-network-interfaces \
        --network-interface-ids $ENI_ID \
        --region $REGION \
        --query 'NetworkInterfaces[0].Association.PublicIp' \
        --output text)

      echo -e "$display_name: ${GREEN}RUNNING${NC} - http://$PUBLIC_IP:8501"
    else
      echo -e "$display_name: ${YELLOW}STARTING...${NC}"
    fi
  else
    echo -e "$display_name: ${RED}STOPPED${NC}"
  fi
}

check_service "plot-agent-base" "Base Agent"
check_service "plot-agent-hitl" "HITL Agent"
check_service "plot-agent-hitl-test" "HITL Test Agent"

echo ""
echo "Commands:"
echo "  Start: ./deployment/start-service.sh [base|hitl|test]"
echo "  Stop:  ./deployment/stop-service.sh [base|hitl|test|all]"
echo "  Logs:  ./deployment/logs.sh [base|hitl|test]"