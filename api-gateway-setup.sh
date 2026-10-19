#!/bin/bash

# Create API Gateway HTTP API
API_ID=$(aws apigatewayv2 create-api \
  --name zoom2youtube \
  --protocol-type HTTP \
  --region eu-central-1 \
  --query 'ApiId' \
  --output text)

echo "API Gateway ID: $API_ID"

# Create integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --region eu-central-1 \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:eu-central-1:179097612774:function:zoom2youtube \
  --payload-format-version 2.0 \
  --query 'IntegrationId' \
  --output text)

echo "Integration ID: $INTEGRATION_ID"

# Create route
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --region eu-central-1 \
  --route-key '$default' \
  --target integrations/$INTEGRATION_ID

# Create stage
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --region eu-central-1 \
  --stage-name '$default' \
  --auto-deploy

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name zoom2youtube \
  --region eu-central-1 \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:eu-central-1:179097612774:$API_ID/*/*"

# Get the API endpoint
API_URL=$(aws apigatewayv2 get-api \
  --api-id $API_ID \
  --region eu-central-1 \
  --query 'ApiEndpoint' \
  --output text)

echo ""
echo "=========================================="
echo "✅ API Gateway URL: $API_URL"
echo "=========================================="

