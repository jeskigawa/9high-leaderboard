#!/usr/bin/env python3
"""Fix nginx config"""
import subprocess
import os

NGINX_CONF = r"""server {
    listen 80;
    server_name _;

    # Admin panel
    location ^~ /leaderboard/admin {
        root /var/www/leaderboard;
        try_files /index.html =404;
        add_header Cache-Control "no-cache";
    }

    # Public leaderboard
    location ^~ /leaderboard/ {
        root /var/www/leaderboard;
        try_files /9high-leaderboard.html =404;
        add_header Cache-Control "no-cache";
    }

    location = /leaderboard {
        return 301 /leaderboard/;
    }

    # Flask API
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60;
    }

    # Flask pages (pokerfans report etc)
    location ^~ /pokerfans {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Uploads served by Flask
    location ^~ /uploads/ {
        proxy_pass http://127.0.0.1:5000;
    }

    # Logo
    location = /logo.svg {
        root /var/www/leaderboard;
    }

    # WordPress
    root /var/www/wordpress;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
    }

    location ~ /\.ht {
        deny all;
    }
}
"""

print("Writing nginx config...")
with open('/etc/nginx/sites-available/leaderboard', 'w') as f:
    f.write(NGINX_CONF)

print("Testing nginx config...")
result = subprocess.run(['nginx', '-t'])
if result.returncode == 0:
    print("Config OK. Reloading nginx...")
    subprocess.run(['systemctl', 'reload', 'nginx'])
    print("Done!")
else:
    print("Config error!")
