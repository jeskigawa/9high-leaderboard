#!/usr/bin/env python3
"""
管理画面(index.html)にnoindexを追加
nginx の /leaderboard/admin/ にも X-Robots-Tag ヘッダーを追加
"""
import subprocess, sys, re

# --- 1. index.html に meta robots noindex 追加 ---
IDX = '/var/www/leaderboard/index.html'
with open(IDX, 'r', encoding='utf-8') as f:
    html = f.read()

NOINDEX = '<meta name="robots" content="noindex, nofollow" />'
if 'noindex' in html:
    print("INFO: index.html にはすでにnoindexがあります")
elif '<meta charset' in html:
    html = html.replace('<meta charset', NOINDEX + '\n  <meta charset')
    with open(IDX, 'w', encoding='utf-8') as f:
        f.write(html)
    print("OK: index.html に noindex 追加")
else:
    print("WARNING: index.html の挿入位置が見つかりません")

# --- 2. nginx に X-Robots-Tag ヘッダー追加 ---
NGINX = '/etc/nginx/sites-available/leaderboard'
with open(NGINX) as f:
    conf = f.read()

import subprocess
subprocess.run(['cp', NGINX, '/tmp/nginx.bak.noindex'])

# /leaderboard/admin/ の専用locationを追加（/leaderboard/ の前に挿入）
ADMIN_LOC = (
    '    # 管理画面 - 検索エンジンにインデックスさせない\n'
    '    location /leaderboard/admin/ {\n'
    '        add_header X-Robots-Tag "noindex, nofollow" always;\n'
    '        proxy_pass http://127.0.0.1:5000/admin/;\n'
    '        proxy_set_header Host $host;\n'
    '        proxy_set_header X-Real-IP $remote_addr;\n'
    '        proxy_set_header X-Forwarded-Proto $scheme;\n'
    '        proxy_read_timeout 300;\n'
    '        proxy_buffering off;\n'
    '    }\n\n'
)

INSERT_BEFORE = '    # リーダーボード: /leaderboard/'
if 'X-Robots-Tag' in conf:
    print("INFO: nginx にはすでにX-Robots-Tagがあります")
elif INSERT_BEFORE in conf:
    conf = conf.replace(INSERT_BEFORE, ADMIN_LOC + INSERT_BEFORE)
    with open(NGINX, 'w') as f:
        f.write(conf)
    r = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    print(r.stderr.strip())
    if r.returncode == 0:
        subprocess.run(['systemctl', 'reload', 'nginx'])
        print("OK: nginx に X-Robots-Tag 追加 + reload")
    else:
        print("nginx エラー! 元に戻します")
        subprocess.run(['cp', '/tmp/nginx.bak.noindex', NGINX])
        sys.exit(1)
else:
    print("WARNING: nginx の挿入位置が見つかりません")
    print("手動で /leaderboard/admin/ ブロックに add_header X-Robots-Tag を追加してください")

print("\n完了! /leaderboard/admin/ はnoindexになりました")
