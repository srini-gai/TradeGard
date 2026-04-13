# TradeGuard — Deployment Guide
# Domain: tradeguard.tech
# Server: srv1581524.hstgr.cloud (Ubuntu 24.04)

---

## Step 1 — Push code to GitHub

On your local machine (Windows):

```bash
# In Cursor terminal
cd c:\Claude_P03\TradeGuard

# Initialise git if not already done
git init
git add .
git commit -m "Initial TradeGuard commit"

# Create repo on GitHub first at https://github.com/new
# Name it: TradeGuard (private repo recommended)

# Then push
git remote add origin https://github.com/YOUR_USERNAME/TradeGuard.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Point domain DNS to your VPS

In your domain registrar (wherever tradeguard.tech is registered):

Add these DNS records:

| Type | Name | Value |
|------|------|-------|
| A | @ | YOUR_VPS_IP |
| A | www | YOUR_VPS_IP |

To get your VPS IP:
```bash
# SSH into server and run:
curl ifconfig.me
```

Wait 5-30 minutes for DNS to propagate.

---

## Step 3 — SSH into your VPS

```bash
ssh root@srv1581524.hstgr.cloud
```

---

## Step 4 — Upload deploy.sh and run first-time setup

```bash
# On the server — download deploy.sh from your GitHub repo
curl -o /root/deploy.sh https://raw.githubusercontent.com/YOUR_USERNAME/TradeGuard/main/deploy.sh
chmod +x /root/deploy.sh

# Edit REPO_URL in deploy.sh first
nano /root/deploy.sh
# Change: REPO_URL="https://github.com/YOUR_USERNAME/TradeGuard.git"

# Run first-time setup (takes 3-5 minutes)
bash /root/deploy.sh --setup
```

---

## Step 5 — Add your Upstox API credentials

```bash
nano /home/tradeguard/app/backend/.env
```

Fill in:
```env
UPSTOX_API_KEY=your_real_api_key
UPSTOX_API_SECRET=your_real_api_secret
UPSTOX_ACCESS_TOKEN=your_real_access_token
VITE_API_URL=https://tradeguard.tech
TRADEGUARD_SCHEDULER=1
```

Save and restart:
```bash
systemctl restart tradeguard
```

---

## Step 6 — Verify deployment

```bash
# Check backend is running
systemctl status tradeguard

# Check health endpoint
curl https://tradeguard.tech/health

# Check logs if something is wrong
journalctl -u tradeguard -n 50 --no-pager
tail -f /var/log/tradeguard/backend.log
```

Open browser: `https://tradeguard.tech`

---

## Step 7 — Set up GitHub Actions (optional — auto deploy on push)

1. Generate SSH key pair on your VPS:
```bash
ssh-keygen -t ed25519 -C "tradeguard-deploy" -f /root/.ssh/deploy_key -N ""
cat /root/.ssh/deploy_key.pub >> /root/.ssh/authorized_keys
cat /root/.ssh/deploy_key  # copy this private key
```

2. Add to GitHub repo:
   - Go to your GitHub repo → Settings → Secrets → Actions
   - Add secret: `VPS_SSH_KEY` = paste the private key content

3. Now every `git push` to `main` auto-deploys to tradeguard.tech

---

## Daily operations

### Update the app manually
```bash
# SSH into server
ssh root@srv1581524.hstgr.cloud
cd /home/tradeguard/app
bash deploy.sh
```

### View live logs
```bash
journalctl -u tradeguard -f
```

### Restart backend
```bash
systemctl restart tradeguard
```

### Check DB
```bash
sqlite3 /home/tradeguard/database/tradeguard.db
.tables
SELECT * FROM signals ORDER BY created_at DESC LIMIT 5;
.quit
```

### SSL certificate renewal (auto — but to force)
```bash
certbot renew --dry-run
```

---

## TradingView Webhook (production)

Once deployed, your webhook URL is:
```
https://tradeguard.tech/webhook/tradingview
```

No ngrok needed in production — use this URL directly in TradingView alerts.

TradingView alert message:
```json
{
  "symbol": "{{ticker}}",
  "action": "BUY_CE",
  "price": {{close}},
  "rsi": 0,
  "timestamp": "{{time}}"
}
```

---

## Scheduler (9:20 AM IST)

The morning screener runs automatically at 9:20 AM IST every weekday
because `TRADEGUARD_SCHEDULER=1` is set in `.env`.

To verify scheduler is running:
```bash
journalctl -u tradeguard | grep "Scheduler started"
journalctl -u tradeguard | grep "screener"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Site not loading | Check `systemctl status tradeguard` and `systemctl status nginx` |
| 502 Bad Gateway | Backend not running — `systemctl restart tradeguard` |
| SSL error | `certbot --nginx -d tradeguard.tech` |
| DB not found | Check `/home/tradeguard/database/` exists and symlink is correct |
| Screener not running | Check `.env` has `TRADEGUARD_SCHEDULER=1` |
| Upstox errors | Refresh access token in Upstox developer portal |
