# 🚀 Zoom2Youtube - Quick Reference

## 🌐 Access
**URL:** https://zoom2youtube.duckdns.org  
**Username:** admin  
**Password:** Zoom2024!

---

## ⚡ Common Commands

### Update Application
```bash
cd ~/workspace/Zoom2Youtube
./update-ec2.sh
```

### View Logs
```bash
ssh -i yossineemanw-fra.pem ubuntu@3.125.153.243 "docker logs -f zoom2youtube"
```

### Restart
```bash
ssh -i yossineemanw-fra.pem ubuntu@3.125.153.243 "docker restart zoom2youtube"
```

### SSH to EC2
```bash
ssh -i ~/workspace/Zoom2Youtube/yossineemanw-fra.pem ubuntu@3.125.153.243
```

---

## 📋 Quick Checks

### Is everything running?
```bash
ssh -i yossineemanw-fra.pem ubuntu@3.125.153.243 "docker ps && sudo systemctl status nginx | grep Active"
```

### Check SSL expiry
```bash
ssh -i yossineemanw-fra.pem ubuntu@3.125.153.243 "sudo certbot certificates"
```

---

## 🔧 Change Password

1. Edit: `credentials/.env`
2. Change: `AUTH_PASSWORD=your_new_password`
3. Run: `./update-ec2.sh`

---

## 💰 Monthly Cost
**Current:** $0 (Free tier)  
**After 12 months:** ~$8.50/month

---

## 📞 Support
**GitHub Issues:** https://github.com/yossi-neeman/Zoom2Youtube/issues
