#!/bin/bash
set -e

DOMAIN="prod.wisualyst.com"

echo "==================================================="
echo "🚀 Wisualyst SSL Setup - prod.wisualyst.com"
echo "==================================================="

# 1. Install Nginx and Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 2. Copy Nginx Configuration
sudo cp nginx_wisualyst.conf /etc/nginx/sites-available/$DOMAIN
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 3. Test and Reload Nginx
sudo nginx -t
sudo systemctl reload nginx

# 4. Generate SSL Certificate via Certbot
echo "🔒 Requesting SSL Certificate from Let's Encrypt for $DOMAIN..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m admin@wisualyst.com --redirect || echo "⚠️ If DNS is propagating, run: sudo certbot --nginx -d $DOMAIN"

echo "==================================================="
echo "🎉 Setup complete! Backend active at: https://$DOMAIN"
echo "==================================================="
