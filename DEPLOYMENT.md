# Zoom2Youtube - Docker & Lambda Deployment Guide

## Architecture Overview

This application supports two deployment modes:
- **Local Development**: Uses local filesystem for storage
- **AWS Lambda**: Uses S3 for storage, automatic scaling, pay-per-use

## Local Development

### Using Docker Compose (Recommended)

```bash
# Build and start the application
docker-compose up --build

# Access at http://localhost:5000
```

### Using Docker directly

```bash
# Build
docker build -f Dockerfile.local -t zoom2youtube:local .

# Run
docker run -p 5000:5000 \
  -v $(pwd)/recordings:/app/recordings \
  -v $(pwd)/credentials:/app/credentials \
  --env-file credentials/.env \
  -e USE_S3_STORAGE=false \
  zoom2youtube:local
```

### Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python web_app.py
```

## AWS Lambda Deployment

### Prerequisites

1. **AWS Account** with:
   - Lambda access
   - S3 bucket for storage
   - ECR for Docker images
   - API Gateway (optional, for custom domain)
   - IAM permissions

2. **AWS CLI** installed and configured:
   ```bash
   aws configure
   ```

3. **Docker** installed and running

### Step 1: Create S3 Bucket

```bash
# Create bucket for recordings and credentials
aws s3 mb s3://zoom2youtube-storage-YOUR-ACCOUNT-ID

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket zoom2youtube-storage-YOUR-ACCOUNT-ID \
  --versioning-configuration Status=Enabled
```

### Step 2: Upload Credentials to S3

```bash
# Upload YouTube client secrets
aws s3 cp credentials/client_secrets.json \
  s3://zoom2youtube-storage-YOUR-ACCOUNT-ID/zoom2youtube/credentials/client_secrets.json

# Upload YouTube token (if exists)
aws s3 cp credentials/youtube_token.pickle \
  s3://zoom2youtube-storage-YOUR-ACCOUNT-ID/zoom2youtube/credentials/youtube_token.pickle
```

### Step 3: Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
  --repository-name zoom2youtube \
  --region us-east-1

# Get login command
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com
```

### Step 4: Build and Push Docker Image

```bash
# Build for Lambda
docker build -t zoom2youtube:lambda .

# Tag for ECR
docker tag zoom2youtube:lambda \
  YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest

# Push to ECR
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest
```

### Step 5: Create Lambda Function

```bash
# Create IAM role for Lambda
aws iam create-role \
  --role-name zoom2youtube-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name zoom2youtube-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create S3 access policy
aws iam put-role-policy \
  --role-name zoom2youtube-lambda-role \
  --policy-name S3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": [
        "arn:aws:s3:::zoom2youtube-storage-YOUR-ACCOUNT-ID/*",
        "arn:aws:s3:::zoom2youtube-storage-YOUR-ACCOUNT-ID"
      ]
    }]
  }'

# Create Lambda function
aws lambda create-function \
  --function-name zoom2youtube \
  --package-type Image \
  --code ImageUri=YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest \
  --role arn:aws:iam::YOUR-ACCOUNT-ID:role/zoom2youtube-lambda-role \
  --timeout 900 \
  --memory-size 2048 \
  --environment "Variables={
    USE_S3_STORAGE=true,
    S3_BUCKET=zoom2youtube-storage-YOUR-ACCOUNT-ID,
    S3_PREFIX=zoom2youtube,
    ZOOM_ACCOUNT_ID=YOUR_ZOOM_ACCOUNT_ID,
    ZOOM_CLIENT_ID=YOUR_ZOOM_CLIENT_ID,
    ZOOM_CLIENT_SECRET=YOUR_ZOOM_CLIENT_SECRET,
    AUTH_USERNAME=admin,
    AUTH_PASSWORD=YOUR_SECURE_PASSWORD,
    AUTH_ENABLED=true
  }"
```

### Step 6: Create Function URL (Simplest option)

```bash
# Create Lambda function URL
aws lambda create-function-url-config \
  --function-name zoom2youtube \
  --auth-type NONE

# Get the URL
aws lambda get-function-url-config \
  --function-name zoom2youtube
```

**OR** use API Gateway for custom domain (see advanced section below)

### Step 7: Test

```bash
# Get the function URL from step 6
# Access it in your browser: https://YOUR-LAMBDA-URL.lambda-url.us-east-1.on.aws/
```

## Environment Variables

### Required for Both Local & Lambda

```bash
# Zoom OAuth Credentials
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret

# Authentication
AUTH_USERNAME=admin
AUTH_PASSWORD=your-secure-password
AUTH_ENABLED=true
```

### Lambda-Specific Variables

```bash
# S3 Storage
USE_S3_STORAGE=true
S3_BUCKET=zoom2youtube-storage-YOUR-ACCOUNT-ID
S3_PREFIX=zoom2youtube  # Optional prefix for organization
```

### Local Development Only

```bash
USE_S3_STORAGE=false  # Force local storage
PORT=5000             # Web server port
```

## Updating Lambda Function

```bash
# Rebuild image
docker build -t zoom2youtube:lambda .

# Tag and push
docker tag zoom2youtube:lambda \
  YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest

# Update Lambda function
aws lambda update-function-code \
  --function-name zoom2youtube \
  --image-uri YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/zoom2youtube:latest
```

## Cost Estimation

### EC2 t3.micro (baseline)
- **Always running**: ~$7-10/month
- **16 hours/day**: ~$5/month with scheduled start/stop

### Lambda + S3 (recommended for 10 min/day)
- **Lambda**: 10 min/day × 30 days × 2GB = 600 GB-seconds/month
  - Free tier: 400,000 GB-seconds/month → **$0**
- **S3 Storage**: ~10GB = **~$0.23/month**
- **S3 Requests**: Negligible with low usage
- **ECR Storage**: ~2GB = **~$0.20/month**
- **Total**: **~$0.50/month** 💰

## Advanced: API Gateway + Custom Domain

If you want a custom domain like `zoom.yourdomain.com`:

```bash
# Create API Gateway REST API
aws apigatewayv2 create-api \
  --name zoom2youtube \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:YOUR-ACCOUNT-ID:function:zoom2youtube

# Configure custom domain with Route 53 and ACM certificate
# (See AWS documentation for detailed steps)
```

## Monitoring & Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/zoom2youtube --follow

# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=zoom2youtube \
  --start-time 2026-10-04T00:00:00Z \
  --end-time 2026-10-05T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum
```

## Troubleshooting

### "Credentials not found" error
- Verify credentials are in S3 at correct path
- Check Lambda IAM role has S3 read permissions

### Lambda timeout
- Increase timeout: `aws lambda update-function-configuration --function-name zoom2youtube --timeout 900`
- Current limit: 15 minutes (900 seconds)

### Memory issues
- Increase memory: `aws lambda update-function-configuration --function-name zoom2youtube --memory-size 3008`

### Local development can't connect
- Check Docker is running
- Verify port 5000 is not in use
- Check credentials/.env file exists

## Security Notes

1. **Never commit credentials to git**
2. **Use AWS Secrets Manager** for production (optional improvement)
3. **Enable CloudWatch Logs encryption**
4. **Use VPC for Lambda** if connecting to private resources
5. **Implement rate limiting** if publicly accessible

## Switching Between Local and Lambda

The application automatically detects the environment:

```python
# storage.py handles this automatically
if os.environ.get('USE_S3_STORAGE') == 'true':
    # Use S3
else:
    # Use local filesystem
```

No code changes needed! Just set environment variables.
