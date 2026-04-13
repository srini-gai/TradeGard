#!/bin/bash
# TradeGuard — Full Deployment Script
# Server: srv1581524.hstgr.cloud
# Domain: tradeguard.tech
# OS: Ubuntu 24.04
#
# Usage:
#   First time:  bash deploy.sh --setup
#   Updates:     bash deploy.sh

set -e  # exit on any error

# ─── Config ───────────────────────────────────────────────────────────────────
APP_DIR="/home/tradeguard/app"
VENV_DIR="$APP_DIR/backend/.venv"
DB_DIR="/home/tradeguard/database"
DOMAIN="tradeguard.tech"
REPO_URL="https://github.com/srini-gai/TradeGard.git"
SERVICE_NAME="tradeguard"
NGINX_CONF="/etc/nginx/sites-available/tradeguard"
# ──────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[TradeGuard]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

SETUP=false
if [[ "$1" == "--setup" ]]; then
  SETUP=true
fi

# ─── SETUP (first time only) ──────────────────────────────────────────────────
if [ "$SETUP" = true ]; then
  log "Starting first-time setup..."

  # System packages
  log "Installing system packages..."
  apt-get update -q
  apt-get install -y -q \
    python3.12 python3.12-venv python3-pip \
    nodejs npm nginx certbot python3-certbot-nginx \
    git curl sqlite3 ufw

  # Node 20 (if not already)
  if ! node --version | grep -q "v20"; then
    log "Installing Node 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  fi

  # Create app user and directories
  log "Creating app directories..."
  mkdir -p "$APP_DIR"
  mkdir -p "$DB_DIR"
  mkdir -p "/var/log/tradeguard"

  # Clone repo
  log "Cloning repository..."
  if [ -d "$APP_DIR/.git" ]; then
    warn "Repo already exists — skipping clone"
  else
    git clone "$REPO_URL" "$APP_DIR"
  fi

  # Python venv
  log "Creating Python virtual environment..."
  python3.12 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip -q
  "$VENV_DIR/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q

  # Frontend build
  log "Building React frontend..."
  cd "$APP_DIR/frontend"
  npm install --silent
  npm run build

  # .env file
  if [ ! -f "$APP_DIR/backend/.env" ]; then
    log "Creating .env file — fill in your Upstox credentials!"
    cat > "$APP_DIR/backend/.env" << 'EOF'
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_ACCESS_TOKEN=your_access_token_here
VITE_API_URL=https://tradeguard.tech
TRADEGUARD_SCHEDULER=1
EOF
    warn "⚠️  Edit $APP_DIR/backend/.env with your real Upstox credentials!"
  fi

  # Symlink DB directory
  ln -sfn "$DB_DIR" "$APP_DIR/database"

  # Nginx config
  log "Configuring Nginx..."
  cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # Frontend — serve React build
    root $APP_DIR/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }

    # TradingView webhook
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 30s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

  ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/tradeguard
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx

  # Systemd service
  log "Creating systemd service..."
  cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=TradeGuard FastAPI Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
StandardOutput=append:/var/log/tradeguard/backend.log
StandardError=append:/var/log/tradeguard/backend.error.log

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl start "$SERVICE_NAME"

  # Firewall
  log "Configuring firewall..."
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable

  # SSL certificate
  log "Issuing SSL certificate for $DOMAIN..."
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos \
    --email admin@$DOMAIN \
    --redirect
  log "SSL certificate issued successfully"

  log "✅ Setup complete!"
  log "Edit your .env: nano $APP_DIR/backend/.env"
  log "Then restart: systemctl restart $SERVICE_NAME"
  log "Visit: https://$DOMAIN"
  exit 0
fi

# ─── UPDATE (subsequent deploys) ─────────────────────────────────────────────
log "Deploying update to $DOMAIN..."

# Pull latest code
log "Pulling latest code from GitHub..."
cd "$APP_DIR"
git pull origin main

# Update Python dependencies
log "Updating Python dependencies..."
"$VENV_DIR/bin/pip" install -r backend/requirements.txt -q

# Rebuild frontend
log "Rebuilding React frontend..."
cd "$APP_DIR/frontend"
npm install --silent
npm run build

# Restart backend
log "Restarting backend service..."
systemctl restart "$SERVICE_NAME"
sleep 3

# Health check
if curl -sf http://127.0.0.1:8000/health > /dev/null; then
  log "✅ Health check passed"
else
  warn "❌ Health check failed — check logs: journalctl -u $SERVICE_NAME -n 50"
  exit 1
fi

log "✅ Deployment complete — https://$DOMAIN"
