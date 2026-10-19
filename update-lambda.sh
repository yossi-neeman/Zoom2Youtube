#!/bin/bash

# Quick update script for Lambda function
# Use this when you make code changes and want to redeploy

set -e

echo "🔄 Updating Lambda function..."

# Get configuration
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME=${1:-zoom2youtube}

ECR_REPO_NAME=$FUNCTION_NAME
ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest"

echo "Region: $AWS_REGION"
echo "Function: $FUNCTION_NAME"
echo ""

# Build image
echo "📦 Building Docker image..."
docker build -t $ECR_REPO_NAME:lambda .

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Tag and push
echo "⬆️  Pushing to ECR..."
docker tag $ECR_REPO_NAME:lambda $ECR_IMAGE_URI
docker push $ECR_IMAGE_URI

# Update Lambda
echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION \
    --image-uri $ECR_IMAGE_URI

# Wait for update to complete
echo "⏳ Waiting for update to complete..."
aws lambda wait function-updated \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION

# Get function URL
FUNCTION_URL=$(aws lambda get-function-url-config \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || echo "No function URL configured")

echo ""
echo "✅ Update complete!"
echo ""
echo "🌐 Function URL: $FUNCTION_URL"
echo ""
echo "View logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
