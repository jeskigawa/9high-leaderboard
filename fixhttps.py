#!/usr/bin/env python3
"""HTTPアクセスを復旧 + HTTPS設定を保持（ConoHaのSGで443を開けた後に使う）"""
import subprocess

NGINX_PATH = '/etc/nginx/sites-available/leaderboard'

# 現在の設定をバックアップ
with open(NGINX_PATH, 'r') as f:
    current = f.read()

backup_path = '/tmp/leaderboard.nginx.bak'
with open(backup_path, 'w') as f:
    f.write(current)
print(f"Backed up to {backup_path}")

# HTTP のみで動くシンプルな設定に戻す（certbotのリダイレクトを除去）
config = """server {
    listen 80;
    server_name 9high.net www.9high.net;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300;
    }
}
"""

with open(NGINX_PATH, 'w') as f:
    f.write(config)
print("HTTP-only config written")

result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

if result.returncode == 0:
    subprocess.run(['systemctl', 'reload', 'nginx'])
    print("nginx reloaded OK")
    print("")
    print("サイトは http://9high.net で復旧しました")
    print("")
    print("次のステップ: ConoHa管理画面でポート443を開けてください")
else:
    print("nginx設定エラー！ バックアップを確認してください:", backup_path)
