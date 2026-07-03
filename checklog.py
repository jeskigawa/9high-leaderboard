#!/usr/bin/env python3
"""最新のエラーログとapp.pyのupload部分を確認する"""
import subprocess
import os

# 最新ログ
print("=== 最新Flaskログ ===")
result = subprocess.run(
    ['journalctl', '-u', 'leaderboard', '-n', '60', '--no-pager'],
    capture_output=True, text=True
)
# 最後の3000文字だけ表示
out = result.stdout
if len(out) > 3000:
    out = out[-3000:]
print(out)

# データディレクトリ確認
print("\n=== データディレクトリ ===")
data_dir = '/var/www/leaderboard/data'
print("存在:", os.path.exists(data_dir))
if os.path.exists(data_dir):
    print("書き込み可能:", os.access(data_dir, os.W_OK))
    files = os.listdir(data_dir)
    print("ファイル数:", len(files))
    for f in files[:10]:
        print(" -", f)

# app.pyのpf_upload部分を表示
print("\n=== app.py pf_upload部分 ===")
APP_PATH = '/var/www/leaderboard/app.py'
with open(APP_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_upload = False
count = 0
for i, line in enumerate(lines, 1):
    if 'def pf_upload' in line:
        in_upload = True
        count = 0
    if in_upload:
        print(f"{i}: {line}", end='')
        count += 1
        if count > 40:
            break
