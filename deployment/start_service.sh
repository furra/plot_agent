#!/bin/bash
# deployment/start-service.sh
# Start a specific ECS service

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$1" ]; then
  echo -e "${RED}Error: Service name required${NC}"
  echo "Usage: ./start_service.sh [base|hitl|test]"
  exit 1
fi

SERVICE_TYPE=$1
STACK_NAME="PlotAgentStack"
REGION="${AWS_REGION:-us-east-1}"

case $SERVICE_TYPE in
  base)
    SERVICE_NAME="plot-agent-base"
    ;;
  hitl)
    SERVICE_NAME="plot-agent-hitl"
    ;;
  test)
    SERVICE_NAME="plot-agent-hitl-test"
    ;;
  *)
    echo -e "${RED}Invalid service type: $SERVICE_TYPE${NC}"
    echo "Valid options: base, hitl, test"
    exit 1
    ;;
esac

echo -e "${YELLOW}Starting $SERVICE_NAME...${NC}"

CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' \
  --output text)

# Update service to run 1 task
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --desired-count 1 \
  --region $REGION > /dev/null

echo -e "${GREEN}✓ Service starting...${NC}"
echo ""
echo "Waiting for task to be running..."

# Wait for task to be running
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION

# Get task IP
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
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

  echo -e "${GREEN}✓ Service is running!${NC}"
  echo ""
  echo "Access your app at:"
  echo -e "${GREEN}http://$PUBLIC_IP:8501${NC}"
  echo ""
  echo "View logs with:"
  echo "  ./deployment/logs.sh $SERVICE_TYPE"
  echo ""
  echo "Stop service with:"
  echo "  ./deployment/stop_service.sh $SERVICE_TYPE"
else
  echo -e "${RED}Failed to get task information${NC}"
fi
