#!/bin/bash

# Zoom2Youtube Lambda Deployment Script
# This script automates the deployment to AWS Lambda

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Zoom2Youtube Lambda Deployment${NC}"
echo "=========================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓${NC} AWS Account ID: $AWS_ACCOUNT_ID"

# Configuration
read -p "AWS Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

read -p "S3 Bucket Name [zoom2youtube-storage-$AWS_ACCOUNT_ID]: " S3_BUCKET
S3_BUCKET=${S3_BUCKET:-zoom2youtube-storage-$AWS_ACCOUNT_ID}

read -p "Lambda Function Name [zoom2youtube]: " FUNCTION_NAME
FUNCTION_NAME=${FUNCTION_NAME:-zoom2youtube}

read -p "Lambda Memory (MB) [2048]: " MEMORY_SIZE
MEMORY_SIZE=${MEMORY_SIZE:-2048}

read -p "Lambda Timeout (seconds, max 900) [900]: " TIMEOUT
TIMEOUT=${TIMEOUT:-900}

ECR_REPO_NAME=$FUNCTION_NAME
ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest"

echo ""
echo "Configuration:"
echo "  Region: $AWS_REGION"
echo "  S3 Bucket: $S3_BUCKET"
echo "  Function: $FUNCTION_NAME"
echo "  ECR Image: $ECR_IMAGE_URI"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Step 1: Create S3 bucket if it doesn't exist
echo ""
echo -e "${YELLOW}Step 1:${NC} Creating S3 bucket..."
if aws s3 ls "s3://$S3_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$S3_BUCKET" --region $AWS_REGION
    echo -e "${GREEN}✓${NC} S3 bucket created"
else
    echo -e "${GREEN}✓${NC} S3 bucket already exists"
fi

# Step 2: Upload credentials to S3
echo ""
echo -e "${YELLOW}Step 2:${NC} Uploading credentials to S3..."
if [ -f "credentials/client_secrets.json" ]; then
    aws s3 cp credentials/client_secrets.json \
        "s3://$S3_BUCKET/zoom2youtube/credentials/client_secrets.json"
    echo -e "${GREEN}✓${NC} client_secrets.json uploaded"
else
    echo -e "${YELLOW}⚠${NC} credentials/client_secrets.json not found - you'll need to upload it manually"
fi

if [ -f "credentials/youtube_token.pickle" ]; then
    aws s3 cp credentials/youtube_token.pickle \
        "s3://$S3_BUCKET/zoom2youtube/credentials/youtube_token.pickle"
    echo -e "${GREEN}✓${NC} youtube_token.pickle uploaded"
fi

# Step 3: Create ECR repository
echo ""
echo -e "${YELLOW}Step 3:${NC} Creating ECR repository..."
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>&1 | grep -q 'RepositoryNotFoundException'; then
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION
    echo -e "${GREEN}✓${NC} ECR repository created"
else
    echo -e "${GREEN}✓${NC} ECR repository already exists"
fi

# Step 4: Build and push Docker image
echo ""
echo -e "${YELLOW}Step 4:${NC} Building Docker image..."
docker build -f Dockerfile.lambda -t $ECR_REPO_NAME:lambda .
echo -e "${GREEN}✓${NC} Docker image built"

echo ""
echo -e "${YELLOW}Step 5:${NC} Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo -e "${GREEN}✓${NC} Logged into ECR"

echo ""
echo -e "${YELLOW}Step 6:${NC} Tagging and pushing image..."
docker tag $ECR_REPO_NAME:lambda $ECR_IMAGE_URI
docker push $ECR_IMAGE_URI
echo -e "${GREEN}✓${NC} Image pushed to ECR"

# Step 7: Create IAM role
echo ""
echo -e "${YELLOW}Step 7:${NC} Creating IAM role..."
ROLE_NAME="$FUNCTION_NAME-role"

if aws iam get-role --role-name $ROLE_NAME 2>&1 | grep -q 'NoSuchEntity'; then
    # Create role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }'
    
    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Create and attach S3 access policy
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name S3Access \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": [\"s3:*\"],
                \"Resource\": [
                    \"arn:aws:s3:::$S3_BUCKET/*\",
                    \"arn:aws:s3:::$S3_BUCKET\"
                ]
            }]
        }"
    
    echo -e "${GREEN}✓${NC} IAM role created"
    echo -e "${YELLOW}⏳${NC} Waiting 10 seconds for IAM role to propagate..."
    sleep 10
else
    echo -e "${GREEN}✓${NC} IAM role already exists"
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Step 8: Get environment variables from .env file
echo ""
echo -e "${YELLOW}Step 8:${NC} Loading environment variables..."

if [ ! -f "credentials/.env" ]; then
    echo -e "${RED}❌ credentials/.env not found${NC}"
    exit 1
fi

# Source the .env file
source credentials/.env

# Create environment variables JSON file
cat > /tmp/lambda_env.json <<EOF
{
  "Variables": {
    "USE_S3_STORAGE": "true",
    "S3_BUCKET": "$S3_BUCKET",
    "S3_PREFIX": "zoom2youtube",
    "ZOOM_ACCOUNT_ID": "$ZOOM_ACCOUNT_ID",
    "ZOOM_CLIENT_ID": "$ZOOM_CLIENT_ID",
    "ZOOM_CLIENT_SECRET": "$ZOOM_CLIENT_SECRET",
    "AUTH_USERNAME": "${AUTH_USERNAME:-admin}",
    "AUTH_PASSWORD": "$AUTH_PASSWORD",
    "AUTH_ENABLED": "${AUTH_ENABLED:-true}"
  }
}
EOF

echo -e "${GREEN}✓${NC} Environment variables loaded"

# Step 9: Create or update Lambda function
echo ""
echo -e "${YELLOW}Step 9:${NC} Creating/updating Lambda function..."

if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>&1 | grep -q 'ResourceNotFoundException'; then
    # Create new function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --package-type Image \
        --code ImageUri=$ECR_IMAGE_URI \
        --role $ROLE_ARN \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment file:///tmp/lambda_env.json
    
    echo -e "${GREEN}✓${NC} Lambda function created"
else
    # Update existing function
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --image-uri $ECR_IMAGE_URI
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment file:///tmp/lambda_env.json
    
    echo -e "${GREEN}✓${NC} Lambda function updated"
fi

# Step 10: Create function URL
echo ""
echo -e "${YELLOW}Step 10:${NC} Creating function URL..."

if aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $AWS_REGION 2>&1 | grep -q 'ResourceNotFoundException'; then
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --auth-type NONE \
        --query 'FunctionUrl' \
        --output text)
    
    # Add permission for public access
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --statement-id FunctionURLAllowPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Function URL created"
else
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --query 'FunctionUrl' \
        --output text)
    echo -e "${GREEN}✓${NC} Function URL already exists"
fi

# Done!
echo ""
echo -e "${GREEN}=========================================="
echo "🎉 Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo "📍 Function URL: $FUNCTION_URL"
echo "📊 CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups/log-group/\$252Faws\$252Flambda\$252F$FUNCTION_NAME"
echo ""
echo "💡 Next steps:"
echo "   1. Open the function URL in your browser"
echo "   2. Log in with your credentials"
echo "   3. Test the upload workflow"
echo ""
echo "🔧 To update the function later, run this script again"
echo ""
