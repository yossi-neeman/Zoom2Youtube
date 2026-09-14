# Oracle Cloud Free Tier Deployment Guide

Deploy Zoom2Youtube on Oracle Cloud's **Always Free** tier - no time limit, no credit card charges after trial.

## Why Oracle Cloud?

✅ **Always Free Resources:**
- 2x AMD Compute VMs (1 vCPU, 1GB RAM each) - **Forever Free**
- OR 4x Arm Ampere A1 cores + 24GB RAM - **Forever Free**
- 200 GB block storage
- 10 TB outbound data transfer per month
- No time limit (unlike AWS 12-month free tier)

## Step 1: Create Oracle Cloud Account

### Sign Up Process:

1. **Go to:** https://www.oracle.com/cloud/free/

2. **Click "Start for free"**

3. **Fill in details:**
   - Email address
   - Country/Territory: Israel (or your country)
   - Cloud Account Name: Choose a unique name (e.g., `zoom2youtube-yourname`)

4. **Home Region:** Choose closest to you
   - **Recommended for Israel:** `eu-frankfurt-1` (Germany) or `me-jeddah-1` (Saudi Arabia)
   - This cannot be changed later!

5. **Account Information:**
   - First Name, Last Name
   - Company Name (can be "Personal")
   - Phone number (required, will receive verification SMS)

6. **Payment Method:**
   - **Credit card required** for verification only
   - ⚠️ Important: You will NOT be charged after the $300 free trial ends
   - Always Free resources remain free forever
   - You can set up billing alerts to prevent charges

7. **Verify Email:**
   - Check your email for verification link
   - Click to verify

8. **Wait for Provisioning:**
   - Takes 5-15 minutes
   - You'll receive email when ready

9. **Set Password:**
   - Create a strong password for your Oracle Cloud account

## Step 2: Launch VM Instance

### Create Compute Instance:

1. **Login to Oracle Cloud Console:**
   - Go to: https://cloud.oracle.com
   - Sign in with your email and password

2. **Navigate to Compute:**
   - Click hamburger menu (☰) top left
   - **Compute** → **Instances**

3. **Create Instance:**
   - Click **"Create Instance"**

4. **Configure Instance:**

   **Name:** `zoom2youtube`

   **Placement:**
   - Leave default (Availability Domain)

   **Image:**
   - Click "Change Image"
   - Select **"Canonical Ubuntu 24.04"** (or 22.04)
   - Click "Select Image"

   **Shape:** (IMPORTANT - Choose Always Free)
   - Click "Change Shape"
   - Select **"VM.Standard.E2.1.Micro"** (Always Free)
     - 1 vCPU, 1 GB RAM
   - OR select **"VM.Standard.A1.Flex"** (Arm, Always Free)
     - Choose: 2 OCPUs, 12 GB RAM (or more, up to 4 OCPUs / 24GB total)
   - Click "Select Shape"

   **Networking:**
   - Create new Virtual Cloud Network (VCN): Yes
   - VCN Name: `zoom2youtube-vcn`
   - Subnet: Create new public subnet
   - **✅ Assign a public IPv4 address:** YES (important!)

   **Add SSH Keys:**
   - **Option A:** Generate SSH key pair (Recommended)
     - Click "Generate a key pair for me"
     - Download both private and public keys
     - Save to safe location (e.g., `~/Downloads/ssh-key-zoom2youtube.key`)
   
   - **Option B:** Upload your own SSH key
     - If you have existing SSH keys

   **Boot Volume:**
   - Leave default (50 GB, Always Free includes up to 200 GB)

5. **Click "Create"**
   - Wait 2-3 minutes for provisioning

6. **Note Your Instance Details:**
   - **Public IP Address** - You'll need this!
   - **Username:** `ubuntu` (for Ubuntu images)

## Step 3: Configure Security (Open Ports)

### Update Security List:

1. **From Instance Details Page:**
   - Click on the **VCN name** (under "Primary VNIC")

2. **Security Lists:**
   - Click **"Security Lists"** on the left menu
   - Click on **"Default Security List for zoom2youtube-vcn"**

3. **Add Ingress Rules:**
   - Click **"Add Ingress Rules"**

   **Rule 1: SSH (if not already present)**
   - Source CIDR: `0.0.0.0/0`
   - Destination Port Range: `22`
   - Description: `SSH`
   - Click "Add Ingress Rules"

   **Rule 2: HTTP**
   - Click "Add Ingress Rules" again
   - Source CIDR: `0.0.0.0/0`
   - Destination Port Range: `80`
   - Description: `HTTP`
   - Click "Add Ingress Rules"

   **Rule 3: HTTPS**
   - Click "Add Ingress Rules" again
   - Source CIDR: `0.0.0.0/0`
   - Destination Port Range: `443`
   - Description: `HTTPS`
   - Click "Add Ingress Rules"

   **Rule 4: Web App**
   - Click "Add Ingress Rules" again
   - Source CIDR: `0.0.0.0/0`
   - Destination Port Range: `5000`
   - Description: `Zoom2Youtube Web App`
   - Click "Add Ingress Rules"

## Step 4: Connect to Your Instance

### Using SSH:

1. **Get your Public IP:**
   - From Compute → Instances → Your instance
   - Copy the **Public IP Address**

2. **Set Key Permissions:** (macOS/Linux)
   ```bash
   chmod 400 ~/Downloads/ssh-key-zoom2youtube.key
   ```

3. **Connect via SSH:**
   ```bash
   ssh -i ~/Downloads/ssh-key-zoom2youtube.key ubuntu@<YOUR_PUBLIC_IP>
   ```

   Example:
   ```bash
   ssh -i ~/Downloads/ssh-key-zoom2youtube.key ubuntu@158.101.123.45
   ```

4. **First Time Connection:**
   - Type `yes` when asked about fingerprint

## Step 5: Install Docker on Oracle Cloud

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Configure Ubuntu firewall
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
sudo netfilter-persistent save

# Log out and back in
exit
```

**SSH back in:**
```bash
ssh -i ~/Downloads/ssh-key-zoom2youtube.key ubuntu@<YOUR_PUBLIC_IP>
```

**Verify Docker:**
```bash
docker --version
```

## Step 6: Deploy Zoom2Youtube

### From Your Local Machine - Upload Credentials:

```bash
# Set your instance IP
export ORACLE_IP=<your-public-ip>
export KEY_FILE=~/Downloads/ssh-key-zoom2youtube.key

# Create directory on Oracle Cloud
ssh -i $KEY_FILE ubuntu@$ORACLE_IP "mkdir -p ~/zoom2youtube/credentials"

# Upload credentials
scp -i $KEY_FILE credentials/.env ubuntu@$ORACLE_IP:~/zoom2youtube/credentials/
scp -i $KEY_FILE credentials/client_secrets.json ubuntu@$ORACLE_IP:~/zoom2youtube/credentials/
scp -i $KEY_FILE credentials/youtube_token.pickle ubuntu@$ORACLE_IP:~/zoom2youtube/credentials/
```

### On Oracle Cloud Instance - Run Docker:

```bash
cd ~/zoom2youtube

# Pull Docker image
docker pull neeman2019/zoom2youtube:latest

# Run container
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

## Step 7: Access Your Application

**Open in browser:**
```
http://<YOUR_ORACLE_IP>:5000
```

Example: `http://158.101.123.45:5000`

## Step 8: Add HTTPS (Optional but Recommended)

### Install Nginx and Let's Encrypt:

**Prerequisites:** You need a domain name pointing to your Oracle IP

```bash
# Install Nginx
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

Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/zoom2youtube /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## Automated Deployment Script

**Use the deployment helper:**

```bash
cd /Users/yossin/workspace/Zoom2Youtube

# Edit script to use Oracle Cloud
./deploy-to-ec2.sh
# When prompted:
# - Enter your Oracle Cloud public IP
# - Enter path to your SSH key: ~/Downloads/ssh-key-zoom2youtube.key
```

## Monitoring and Maintenance

### Check Resource Usage:

```bash
# SSH into instance
ssh -i $KEY_FILE ubuntu@$ORACLE_IP

# Check memory
free -h

# Check disk space
df -h

# Check Docker stats
docker stats zoom2youtube

# View logs
docker logs zoom2youtube --tail 100
```

### Update Application:

```bash
# SSH into instance
ssh -i $KEY_FILE ubuntu@$ORACLE_IP

cd ~/zoom2youtube

# Pull latest image
docker pull neeman2019/zoom2youtube:latest

# Restart container
docker stop zoom2youtube
docker rm zoom2youtube

# Run new container (same command as before)
docker run -d --name zoom2youtube --restart unless-stopped \
  -p 5000:5000 \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest
```

### Backup Credentials:

```bash
# From local machine
scp -i $KEY_FILE -r ubuntu@$ORACLE_IP:~/zoom2youtube/credentials ./backup-oracle-$(date +%Y%m%d)
```

## Free Domain Options

1. **DuckDNS** (Recommended for Oracle Cloud)
   - https://www.duckdns.org
   - Free subdomain: `zoom2youtube.duckdns.org`
   - Easy setup with dynamic DNS

2. **Freenom**
   - https://www.freenom.com
   - Free .tk, .ml, .ga, .cf, .gq domains
   - Requires manual renewal every 12 months

3. **No-IP**
   - https://www.noip.com
   - Free dynamic DNS

## Cost Breakdown

**Always Free Resources (Forever):**
- ✅ VM.Standard.E2.1.Micro: FREE
- ✅ VM.Standard.A1.Flex (up to 4 cores): FREE
- ✅ 200 GB storage: FREE
- ✅ 10 TB monthly data transfer: FREE
- ✅ No time limit: FREE

**Total Monthly Cost: $0 (Forever)**

## Troubleshooting

### Can't connect to web interface?

1. **Check instance is running:**
   - Oracle Console → Compute → Instances
   - Should show "Running" in green

2. **Check Docker container:**
   ```bash
   docker ps
   docker logs zoom2youtube
   ```

3. **Check firewall:**
   ```bash
   sudo iptables -L -n | grep 5000
   ```

4. **Check Security List:**
   - Oracle Console → Networking → VCN
   - Verify port 5000 is open

### YouTube authentication issues?

Upload fresh token:
```bash
# On local machine
cd /Users/yossin/workspace/Zoom2Youtube
./refresh_youtube_auth.sh

# Upload to Oracle Cloud
scp -i $KEY_FILE credentials/youtube_token.pickle ubuntu@$ORACLE_IP:~/zoom2youtube/credentials/

# Restart container
ssh -i $KEY_FILE ubuntu@$ORACLE_IP "docker restart zoom2youtube"
```

### Out of memory?

Upgrade to Arm Ampere (if using E2.1.Micro):
- Better performance
- More RAM (up to 24 GB free)
- Still Always Free!

## Security Best Practices

1. **Change SSH port** (optional):
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Change Port 22 to Port 2222
   sudo systemctl restart sshd
   ```

2. **Setup firewall:**
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw allow 5000
   sudo ufw enable
   ```

3. **Add basic auth** (see SECURITY.md)

4. **Use HTTPS** with domain + Let's Encrypt

## Summary

**Quick Commands:**

```bash
# 1. Create Oracle Cloud account
# 2. Launch VM.Standard.E2.1.Micro instance
# 3. Download SSH key

# 4. Connect
ssh -i ~/Downloads/ssh-key-zoom2youtube.key ubuntu@<IP>

# 5. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
exit

# 6. Upload credentials (from local)
scp -i KEY credentials/* ubuntu@<IP>:~/zoom2youtube/credentials/

# 7. Run Docker (on Oracle Cloud)
ssh -i KEY ubuntu@<IP>
docker run -d --name zoom2youtube -p 5000:5000 \
  --env-file ~/zoom2youtube/credentials/.env \
  -v ~/zoom2youtube/credentials:/app/credentials \
  -v ~/zoom2youtube/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest

# 8. Access: http://<IP>:5000
```

**For production:** Add domain + HTTPS + basic auth

---

**Next Steps:** See SECURITY.md for production hardening.
