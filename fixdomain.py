#!/usr/bin/env python3
"""Update nginx config with domain name and reload"""
import subprocess

NGINX_PATH = '/etc/nginx/sites-available/leaderboard'

with open(NGINX_PATH, 'r') as f:
    conf = f.read()

conf = conf.replace('server_name _;', 'server_name 9high.net www.9high.net;')

with open(NGINX_PATH, 'w') as f:
    f.write(conf)

print("nginx config updated")

result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

if result.returncode == 0:
    subprocess.run(['systemctl', 'reload', 'nginx'])
    print("nginx reloaded OK")
else:
    print("nginx config error!")
