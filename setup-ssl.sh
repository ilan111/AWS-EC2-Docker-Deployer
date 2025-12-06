#!/bin/bash

# SSL Certificate Setup Script
# Run this ONCE to get your Let's Encrypt certificates

set -e

# Configuration
DOMAIN="localhost"  # CHANGE THIS TO YOUR DOMAIN
EMAIL="your-email@example.com"  # CHANGE THIS TO YOUR EMAIL

echo "Setting up SSL certificates for $DOMAIN"

# Create directories
mkdir -p nginx
mkdir -p certbot/conf
mkdir -p certbot/www

# Create temporary nginx config for initial cert request
cat > nginx/nginx.conf <<EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $DOMAIN www.$DOMAIN;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            proxy_pass http://streamlit:8501;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
    }
}
EOF

echo "Temporary nginx config created"

# Start nginx and certbot
echo "Starting nginx..."
docker compose up -d nginx

sleep 5

# Request certificate
echo "Requesting SSL certificate from Let's Encrypt..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

if [ $? -eq 0 ]; then
    echo "Certificate obtained successfully!"
    
    # Create final nginx config with SSL
    cat > nginx/nginx.conf <<EOF
events {
    worker_connections 1024;
}

http {
    # HTTP - Redirect to HTTPS
    server {
        listen 80;
        server_name $DOMAIN www.$DOMAIN;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$host\$request_uri;
        }
    }

    # HTTPS
    server {
        listen 443 ssl http2;
        server_name $DOMAIN www.$DOMAIN;

        ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location / {
            proxy_pass http://streamlit:8501;
            proxy_http_version 1.1;
            
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # WebSocket support
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
EOF

    echo "Final nginx config created with SSL"
    
    # Restart nginx with SSL config
    echo "Restarting nginx with SSL..."
    docker compose restart nginx
    
    echo ""
    echo "SSL setup complete!"
    echo "Your site is now available at: https://$DOMAIN"
    echo "Certificates will auto-renew every 12 hours"
    
else
    echo "Certificate request failed!"
    echo "Make sure:"
    echo "1. Your domain $DOMAIN points to this server's IP"
    echo "2. Ports 80 and 443 are open"
    echo "3. No other service is using port 80"
    exit 1
fi