# AWS EC2 Deployment Guide

Deploy Zoom2Youtube web interface on AWS EC2 free tier for external web access.

## Prerequisites

1. AWS Account (free tier eligible)
2. Your credentials files:
   - `credentials/.env` (Zoom API keys)
   - `credentials/client_secrets.json` (YouTube OAuth)
   - `credentials/youtube_token.pickle` (YouTube auth token)

## Quick Start

### Option 1: AWS EC2 Free Tier (Recommended)

**Instance Type:** t2.micro (1 vCPU, 1GB RAM) - Free for 12 months

#### Step 1: Launch EC2 Instance

1. **Go to AWS EC2 Console**: https://console.aws.amazon.com/ec2/
2. **Click "Launch Instance"**
3. **Configure:**
   - **Name:** Zoom2Youtube
   - **AMI:** Ubuntu Server 24.04 LTS (Free tier eligible)
   - **Instance Type:** t2.micro
   - **Key Pair:** Create new or select existing (download .pem file)
   - **Network Settings:**
     - ✅ Allow SSH traffic from: My IP (or anywhere)
     - ✅ Allow HTTP traffic from: Internet
     - ✅ Allow HTTPS traffic from: Internet
   - **Storage:** 8 GB (default, free tier)
4. **Click "Launch Instance"**

#### Step 2: Configure Security Group

After launch, update the security group:

1. Go to **EC2 → Security Groups**
2. Select your instance's security group
3. **Add Inbound Rule:**
   - **Type:** Custom TCP
   - **Port Range:** 5000
   - **Source:** 0.0.0.0/0 (anywhere)
   - **Description:** Web app access

#### Step 3: Connect to Your Instance

```bash
# Get your instance's public IP from EC2 console
export EC2_IP=<your-instance-public-ip>

# Connect via SSH (replace with your key path)
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@$EC2_IP
```

#### Step 4: Install Docker on EC2

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Log out and back in for group changes
exit
# SSH back in
ssh -i your-key.pem ubuntu@$EC2_IP

# Verify Docker
docker --version
```

#### Step 5: Upload Credentials

**From your local machine:**

```bash
# Create credentials directory on EC2
ssh -i your-key.pem ubuntu@$EC2_IP "mkdir -p ~/zoom2youtube/credentials"

# Copy credentials files
scp -i your-key.pem credentials/.env ubuntu@$EC2_IP:~/zoom2youtube/credentials/
scp -i your-key.pem credentials/client_secrets.json ubuntu@$EC2_IP:~/zoom2youtube/credentials/
scp -i your-key.pem credentials/youtube_token.pickle ubuntu@$EC2_IP:~/zoom2youtube/credentials/
```

#### Step 6: Run Docker Container

**On EC2:**

```bash
cd ~/zoom2youtube

# Pull the latest image
docker pull neeman2019/zoom2youtube:latest

# Run the container
docker run -d \
  --name zoom2youtube \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest

# Check logs
docker logs -f zoom2youtube
```

#### Step 7: Access Your Web Interface

Open in your browser:
```
http://<your-ec2-public-ip>:5000
```

**Example:** `http://3.85.123.45:5000`

---

## Security Improvements

### 1. Use HTTPS with Let's Encrypt (Recommended)

Install Nginx as reverse proxy with SSL:

```bash
# Install Nginx and Certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/zoom2youtube
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and get SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/zoom2youtube /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate (requires domain pointing to your EC2 IP)
sudo certbot --nginx -d your-domain.com
```

### 2. Add Basic Authentication

Update docker run command:
```bash
docker run -d \
  --name zoom2youtube \
  --restart unless-stopped \
  -p 5000:5000 \
  -e BASIC_AUTH_USERNAME=admin \
  -e BASIC_AUTH_PASSWORD=your-secure-password \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest
```

### 3. Restrict Access by IP

In Security Group, change port 5000 rule:
- **Source:** Custom → Your office/home IP address

---

## Alternative Free Options

### Option 2: AWS Lightsail ($0 for 3 months trial)

1. **Go to:** https://lightsail.aws.amazon.com/
2. **Create Instance:**
   - **Platform:** Linux/Unix
   - **Blueprint:** OS Only → Ubuntu 24.04
   - **Plan:** $3.50/month (750 hours free trial)
3. **Follow same Docker installation steps**

### Option 3: Oracle Cloud (Always Free)

Oracle offers **always free** instances:
- **2x AMD E2.1 Micro VMs** (1 vCPU, 1GB RAM each)
- **4x Arm Ampere A1 cores** (24GB RAM total)

1. **Sign up:** https://www.oracle.com/cloud/free/
2. **Create Instance:** Compute → VM.Standard.E2.1.Micro
3. **Follow Ubuntu setup steps**

---

## Domain Setup (Optional)

### Free Domain Options:
- **Freenom:** Free .tk, .ml, .ga domains
- **DuckDNS:** Free subdomain (zoom2youtube.duckdns.org)
- **No-IP:** Free dynamic DNS

### Point Domain to EC2:
1. Get EC2 Elastic IP (static IP):
   - EC2 Console → Elastic IPs → Allocate
   - Associate with your instance
2. Update DNS A record:
   - Point `your-domain.com` to Elastic IP

---

## Maintenance

### Update Docker Image

```bash
# On EC2
docker pull neeman2019/zoom2youtube:latest
docker stop zoom2youtube
docker rm zoom2youtube

# Run with new image (same command as before)
docker run -d --name zoom2youtube ...
```

### Check Logs

```bash
docker logs -f zoom2youtube
```

### Restart Container

```bash
docker restart zoom2youtube
```

### Backup Credentials

```bash
# From local machine
scp -i your-key.pem -r ubuntu@$EC2_IP:~/zoom2youtube/credentials ./backup-$(date +%Y%m%d)
```

---

## Costs Estimate

**AWS EC2 Free Tier:**
- ✅ t2.micro instance: **FREE** for 12 months (750 hours/month)
- ✅ 30 GB storage: **FREE** (only using 8GB)
- ✅ 100 GB data transfer out: **FREE** per month
- ⚠️ Elastic IP: **FREE** if attached to running instance

**After free tier (month 13+):**
- t2.micro: ~$8.50/month
- 8 GB storage: ~$0.80/month
- Data transfer: $0.09/GB over 100GB
- **Total:** ~$10-15/month

**Cost reduction:**
- Use Oracle Cloud Always Free tier (no time limit)
- Use AWS Lightsail ($3.50/month with predictable pricing)

---

## Troubleshooting

### Can't access from browser?

1. **Check Security Group:** Ensure port 5000 is open
2. **Check Docker:** `docker logs zoom2youtube`
3. **Check EC2 status:** Instance should be running
4. **Try HTTP not HTTPS:** `http://` not `https://`

### YouTube authentication issues?

Refresh the token locally, then upload:
```bash
# On local machine
./refresh_youtube_auth.sh

# Upload to EC2
scp -i your-key.pem credentials/youtube_token.pickle ubuntu@$EC2_IP:~/zoom2youtube/credentials/

# Restart container
ssh -i your-key.pem ubuntu@$EC2_IP "docker restart zoom2youtube"
```

### Out of memory?

t2.micro has only 1GB RAM. If issues occur:
1. **Monitor:** `docker stats zoom2youtube`
2. **Upgrade:** to t2.small (2GB RAM) - $16.79/month
3. **Or use Oracle Cloud:** Free 24GB Ampere instance

---

## Summary

**Quick Commands:**

```bash
# Deploy in 5 minutes
ssh -i your-key.pem ubuntu@$EC2_IP
curl -fsSL https://get.docker.com | sh
mkdir -p ~/zoom2youtube/credentials
# Upload credentials (from local)
# Run docker container
docker run -d --name zoom2youtube -p 5000:5000 \
  --env-file ~/zoom2youtube/credentials/.env \
  -v ~/zoom2youtube/credentials:/app/credentials \
  -v ~/zoom2youtube/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest
```

**Access:** `http://<ec2-ip>:5000`

**For production:** Add HTTPS with Nginx + Let's Encrypt + domain name.
