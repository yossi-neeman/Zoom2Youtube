# Security Best Practices

## For Public Internet Deployment

When running on AWS EC2 or any public server, follow these security practices:

## 1. Add Basic Authentication

Update `web_app.py` to require login before accessing the interface.

Install required package:
```bash
pip install Flask-HTTPAuth
```

Add to `requirements.txt`:
```
Flask-HTTPAuth>=4.8.0
```

Add to `web_app.py`:
```python
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash

auth = HTTPBasicAuth()

# Set credentials via environment variables
users = {
    os.environ.get('ADMIN_USERNAME', 'admin'): os.environ.get('ADMIN_PASSWORD', 'changeme')
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

@app.route('/')
@auth.login_required
def index():
    return render_template('index.html')
```

Set credentials when running:
```bash
docker run -d \
  --name zoom2youtube \
  -p 5000:5000 \
  -e ADMIN_USERNAME=yourusername \
  -e ADMIN_PASSWORD=your-secure-password \
  --env-file credentials/.env \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  neeman2019/zoom2youtube:latest
```

## 2. Use HTTPS (Recommended for Production)

### Option A: Nginx Reverse Proxy with Let's Encrypt

```bash
# Install on EC2
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx
sudo tee /etc/nginx/sites-available/zoom2youtube << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/zoom2youtube /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate (requires domain pointing to EC2)
sudo certbot --nginx -d your-domain.com
```

### Option B: Cloudflare (Free SSL + DDoS Protection)

1. Sign up at https://cloudflare.com (free plan)
2. Add your domain
3. Update nameservers
4. Enable "Full (Strict)" SSL mode
5. Enable "Always Use HTTPS"

## 3. Restrict Network Access

### AWS Security Group Rules:

**Minimum (less secure):**
- Port 5000: Your office/home IP only
- Port 22 (SSH): Your IP only

**Recommended (with Nginx):**
- Port 80: 0.0.0.0/0 (HTTP, redirects to HTTPS)
- Port 443: 0.0.0.0/0 (HTTPS)
- Port 22 (SSH): Your IP only
- Port 5000: localhost only (remove from security group)

### VPN Access (Most Secure):

Use AWS VPN or Tailscale to access privately:

**Tailscale (easiest):**
```bash
# On EC2
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# On your computer
# Install Tailscale and connect
# Access via: http://100.x.x.x:5000
```

## 4. Environment Variables Security

**Never expose `.env` file publicly!**

Current setup is secure:
- ✅ `.env` is in `.gitignore`
- ✅ Mounted as volume in Docker (not in image)
- ✅ Not accessible via web interface

## 5. Regular Updates

Keep system and Docker image updated:

```bash
# On EC2
sudo apt-get update && sudo apt-get upgrade -y
docker pull neeman2019/zoom2youtube:latest
docker restart zoom2youtube
```

## 6. Monitoring and Alerts

### CloudWatch Alarms (AWS)

Set up alerts for:
- High CPU usage (>80%)
- High memory usage (>90%)
- Disk space (>80%)

### Log Monitoring

```bash
# View real-time logs
docker logs -f zoom2youtube

# Search for errors
docker logs zoom2youtube 2>&1 | grep -i error
```

## 7. Backup Strategy

### Automated Backup Script

Create `backup.sh` on EC2:
```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup credentials
tar -czf $BACKUP_DIR/credentials_$DATE.tar.gz \
  ~/zoom2youtube/credentials/

# Keep only last 7 days
find $BACKUP_DIR -name "credentials_*.tar.gz" -mtime +7 -delete

echo "Backup completed: credentials_$DATE.tar.gz"
```

Schedule with cron:
```bash
crontab -e
# Add: Daily backup at 2 AM
0 2 * * * /home/ubuntu/backup.sh
```

## 8. Firewall (UFW)

```bash
# On EC2 Ubuntu
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5000/tcp  # Web app (if not using Nginx)
sudo ufw enable
```

## 9. Fail2Ban (Prevent Brute Force)

```bash
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 10. Audit Log

Add logging to `web_app.py`:

```python
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='/app/logs/access.log',
    level=logging.INFO,
    format='%(asctime)s - %(remote_addr)s - %(message)s'
)

@app.before_request
def log_request():
    logging.info(f"{request.method} {request.path} - User: {request.remote_addr}")
```

---

## Security Checklist

Before going to production:

- [ ] Basic authentication enabled
- [ ] HTTPS configured (Nginx + Let's Encrypt or Cloudflare)
- [ ] Security group rules restricted
- [ ] Strong passwords set
- [ ] `.env` file secured
- [ ] Regular backups scheduled
- [ ] Monitoring enabled
- [ ] Firewall configured
- [ ] SSH key-only access (disable password auth)
- [ ] System updates automated
- [ ] Fail2Ban installed
- [ ] Logs reviewed regularly

---

## Quick Security Setup

**5-minute security boost:**

```bash
# 1. Enable firewall
sudo ufw allow 22 && sudo ufw allow 5000 && sudo ufw enable

# 2. Add basic auth
docker run -d --name zoom2youtube \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=$(openssl rand -base64 12) \
  ...other options...

# 3. Restrict security group to your IP
# (Do this in AWS Console)

# 4. Enable auto-updates
sudo apt-get install -y unattended-upgrades
```

**For production, follow full HTTPS setup with domain + Let's Encrypt.**
