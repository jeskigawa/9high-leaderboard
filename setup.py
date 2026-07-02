#!/usr/bin/env python3
"""Deployment setup script for 9high leaderboard"""
import subprocess
import os
import sys

def run(cmd):
    if isinstance(cmd, str):
        print(f"  $ {cmd}")
        r = subprocess.run(cmd, shell=True)
    else:
        print(f"  $ {' '.join(cmd)}")
        r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  [warning] exit code {r.returncode}")
    return r

# ---- nginx config ----
NGINX_CONF = r"""server {
    listen 80;
    server_name _;

    # Public leaderboard
    location = /leaderboard/ {
        root /var/www/leaderboard;
        try_files /9high-leaderboard.html =404;
    }
    location = /leaderboard {
        return 301 /leaderboard/;
    }

    # Admin panel
    location = /leaderboard/admin {
        root /var/www/leaderboard;
        try_files /index.html =404;
    }
    location = /leaderboard/admin/ {
        return 301 /leaderboard/admin;
    }

    # Flask API
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60;
    }

    # Uploads served by Flask
    location /uploads/ {
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

# ---- systemd service ----
SERVICE_CONF = """[Unit]
Description=9high Leaderboard Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/leaderboard
Environment=PATH=/var/www/leaderboard/venv/bin
ExecStart=/var/www/leaderboard/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

print("=== [1/6] Installing Python packages ===")
run(['/var/www/leaderboard/venv/bin/pip', 'install', '-r',
     '/var/www/leaderboard/requirements.txt', '-q'])

print("\n=== [2/6] Fixing file permissions ===")
run(['chown', '-R', 'www-data:www-data', '/var/www/leaderboard'])
run(['chmod', '-R', '755', '/var/www/leaderboard'])
run(['chmod', '-R', '775', '/var/www/leaderboard/data'])

print("\n=== [3/6] Writing nginx config ===")
with open('/etc/nginx/sites-available/leaderboard', 'w') as f:
    f.write(NGINX_CONF)
symlink = '/etc/nginx/sites-enabled/leaderboard'
if os.path.exists(symlink):
    os.remove(symlink)
os.symlink('/etc/nginx/sites-available/leaderboard', symlink)
default = '/etc/nginx/sites-enabled/default'
if os.path.exists(default):
    os.remove(default)
    print("  removed default nginx site")
print("  done")

print("\n=== [4/6] Writing systemd service ===")
with open('/etc/systemd/system/leaderboard.service', 'w') as f:
    f.write(SERVICE_CONF)
run(['systemctl', 'daemon-reload'])
run(['systemctl', 'enable', 'leaderboard'])
print("  done")

print("\n=== [5/6] Starting leaderboard service ===")
run(['systemctl', 'restart', 'leaderboard'])
import time; time.sleep(2)
run(['systemctl', 'status', 'leaderboard', '--no-pager', '-l'])

print("\n=== [6/6] Restarting nginx ===")
result = run(['nginx', '-t'])
run(['systemctl', 'restart', 'nginx'])
run(['systemctl', 'status', 'nginx', '--no-pager'])

print("\n========================================")
print("Setup complete!")
print("Public:  http://160.251.123.221/leaderboard/")
print("Admin:   http://160.251.123.221/leaderboard/admin")
print("========================================")
